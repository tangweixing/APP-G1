#include <string>
#include <vector>
#include <iostream>
#include <cmath>

#include <ros/ros.h>
#include <nav_msgs/Odometry.h>
#include <nav_msgs/Path.h>
#include <geometry_msgs/PointStamped.h>
#include <geometry_msgs/PoseStamped.h>
#include <std_msgs/Bool.h>
#include <tf/transform_listener.h>
#include <std_msgs/ColorRGBA.h>
#include <visualization_msgs/MarkerArray.h>

std::string odom_topic = "slam_odom";
std::string path_topic = "teach_path";
float distance_thre = 2.0;
float distance_tole = 1.9;
float distance_step = 0.1;

// 新增：曲率相关参数
double min_lookahead_distance = 1.0;  // 最小前瞻距离（米）
double max_lookahead_distance = 2.0;  // 最大前瞻距离（米）
double high_curvature_threshold = 0.5; // 高曲率阈值

float vehicleX = 0, vehicleY = 0, vehicleZ = 0;
double curTime = 0;

bool Flag_get_new_path = false;
bool Flag_finish_path = false;
bool Flag_switch_goal = false;

tf::TransformListener* tf_listener = nullptr;
std::vector<geometry_msgs::PoseStamped> way_point_array;
std::vector<geometry_msgs::PoseStamped> last_path_array;
std::vector<double> curvature_values;  // 新增：存储每个点的曲率值

ros::Publisher pubWaypoint;
ros::Publisher pubPathVis;

// 新增：计算路径点的曲率
double calculateCurvature(const std::vector<geometry_msgs::PoseStamped>& path, size_t index) {
    if (index == 0 || index >= path.size() - 1) {
        return 0.0;  // 端点曲率为0
    }
    
    const auto& p1 = path[index - 1].pose.position;
    const auto& p2 = path[index].pose.position;
    const auto& p3 = path[index + 1].pose.position;
    
    // 计算三点形成的角度变化
    double dx1 = p2.x - p1.x;
    double dy1 = p2.y - p1.y;
    double dx2 = p3.x - p2.x;
    double dy2 = p3.y - p2.y;
    
    double len1 = sqrt(dx1*dx1 + dy1*dy1);
    double len2 = sqrt(dx2*dx2 + dy2*dy2);
    
    if (len1 < 1e-6 || len2 < 1e-6) {
        return 0.0;
    }
    
    // 归一化向量
    dx1 /= len1; dy1 /= len1;
    dx2 /= len2; dy2 /= len2;
    
    // 计算角度变化
    double dot_product = dx1*dx2 + dy1*dy2;
    dot_product = std::max(-1.0, std::min(1.0, dot_product));  // 限制范围
    double angle_change = acos(dot_product);
    
    // 曲率 = 角度变化 / 平均弦长
    double avg_length = (len1 + len2) / 2.0;
    return angle_change / std::max(avg_length, 1e-6);
}

// 新增：根据曲率计算动态前瞻距离
double calculateLookaheadDistance(double curvature) {
    double base_distance;
    
    if (curvature < high_curvature_threshold) {
        // 低曲率：使用最大前瞻距离
        base_distance = max_lookahead_distance;
    } else {
        // 高曲率：根据曲率线性插值
        double curvature_factor = std::min(curvature / high_curvature_threshold, 2.0);
        base_distance = max_lookahead_distance - (max_lookahead_distance - min_lookahead_distance) * (curvature_factor - 1.0);
        base_distance = std::max(base_distance, min_lookahead_distance);
    }
    
    return base_distance;
}

void poseHandler(const nav_msgs::Odometry::ConstPtr& pose)
{
  geometry_msgs::PoseStamped local_pose, map_pose;
  local_pose.header = pose->header;
  local_pose.pose = pose->pose.pose;

  try
  {
    tf_listener->transformPose("map", local_pose, map_pose);
    curTime = map_pose.header.stamp.toSec();

    vehicleX = map_pose.pose.position.x;
    vehicleY = map_pose.pose.position.y;
    vehicleZ = map_pose.pose.position.z;
  }
  catch (tf::TransformException& ex)
  {
    ROS_WARN("TF transform failed: %s", ex.what());
  }
}

void pathHandler(const nav_msgs::Path::ConstPtr& path)
{
  if (path->poses.empty()) return;

  bool path_changed = path->poses.size() != last_path_array.size() ||
    path->poses.back().pose.position.x != last_path_array.back().pose.position.x ||
    path->poses.back().pose.position.y != last_path_array.back().pose.position.y;

  if (!path_changed) return;

  Flag_get_new_path = true;
  way_point_array.clear();
  // stair_flags.clear();
  last_path_array = path->poses;

  double temp_x = path->poses[0].pose.position.x;
  double temp_y = path->poses[0].pose.position.y;
  double temp_z = path->poses[0].pose.position.z;

  // 1. 采样路径点
  for (const auto& pose_stamped : path->poses)
  {
    double dx = pose_stamped.pose.position.x - temp_x;
    double dy = pose_stamped.pose.position.y - temp_y;
    double dz = pose_stamped.pose.position.z - temp_z;

    double distance = sqrt(dx*dx + dy*dy + dz*dz);
    if (distance > distance_step)
    {
      way_point_array.push_back(pose_stamped);
      temp_x = pose_stamped.pose.position.x;
      temp_y = pose_stamped.pose.position.y;
      temp_z = pose_stamped.pose.position.z;
    }
  }
  way_point_array.push_back(path->poses.back());

  curvature_values.resize(way_point_array.size(), 0.0);  // 新增：初始化曲率数组

  // 2. 计算每个点的曲率
  for (size_t i = 0; i < way_point_array.size(); ++i) {
    curvature_values[i] = calculateCurvature(way_point_array, i);
  }

  // 3. 发布可视化路径
  nav_msgs::Path vis_path;
  vis_path.header.frame_id = "map";
  vis_path.header.stamp = ros::Time::now();
  for (size_t i = 0; i < way_point_array.size(); ++i)
  {
    vis_path.poses.push_back(way_point_array[i]);
  }
  pubPathVis.publish(vis_path);
}

int main(int argc, char** argv)
{
  ros::init(argc, argv, "path2waypoint");
  ros::NodeHandle nh;
  ros::NodeHandle nhPrivate("~");

  nhPrivate.getParam("odom_topic", odom_topic);
  nhPrivate.getParam("path_topic", path_topic);
  nhPrivate.getParam("distance_thre", distance_thre);

  tf::TransformListener listener;
  tf_listener = &listener;

  ros::Subscriber subPose = nh.subscribe<nav_msgs::Odometry>(odom_topic, 5, poseHandler);
  ros::Subscriber subPath = nh.subscribe<nav_msgs::Path>(path_topic, 5, pathHandler);

  pubWaypoint = nh.advertise<geometry_msgs::PointStamped>("/way_point", 5);
  pubPathVis   = nh.advertise<nav_msgs::Path>("/path_with_stairs", 1);

  geometry_msgs::PointStamped waypointMsgs;
  waypointMsgs.header.frame_id = "map";
  geometry_msgs::PoseStamped goal_point;
  int path_index = 0;

  ros::Rate rate(50);
  while (ros::ok())
  {
    ros::spinOnce();

    if (!way_point_array.empty())
    {
      if (Flag_get_new_path)
      {
        goal_point = way_point_array.front();
        path_index = 0;
        Flag_switch_goal = true;
        Flag_get_new_path = false;
        Flag_finish_path = false;
      }
      else
      {
        int closest_index = 0;
        double min_dist = 1e9;
        for (int i = 0; i < (int)way_point_array.size(); ++i)
        {
          double d = sqrt(
            pow(way_point_array[i].pose.position.x - vehicleX, 2) +
            pow(way_point_array[i].pose.position.y - vehicleY, 2) +
            pow(way_point_array[i].pose.position.z - vehicleZ, 2));
          if (d < min_dist)
          {
            min_dist = d;
            closest_index = i;
          }
        }

        // 计算最近点和上次前瞻点之间线段的最大曲率
        double segment_curvature = 0.0;
        int start_index = std::min(closest_index, path_index);
        int end_index = std::max(closest_index, path_index);
        
        for (int i = start_index; i <= end_index && i < (int)curvature_values.size(); ++i) {
          segment_curvature = std::max(segment_curvature, curvature_values[i]);
        }
        
        // 如果线段为空，使用最近点的曲率
        if (start_index == end_index) {
          segment_curvature = (closest_index < (int)curvature_values.size()) ? curvature_values[closest_index] : 0.0;
        }
        
        double current_distance_thre = calculateLookaheadDistance(segment_curvature);

        double accum_dist = 0.0;
        int target_index = closest_index;
        for (int i = closest_index + 1; i < (int)way_point_array.size(); ++i)
        {
          double seg_d = sqrt(
            pow(way_point_array[i].pose.position.x - way_point_array[i - 1].pose.position.x, 2) +
            pow(way_point_array[i].pose.position.y - way_point_array[i - 1].pose.position.y, 2) +
            pow(way_point_array[i].pose.position.z - way_point_array[i - 1].pose.position.z, 2));
          accum_dist += seg_d;
          
          if (accum_dist >= current_distance_thre)
          {
            target_index = i;
            break;
          }
        }

        if (accum_dist < current_distance_thre)
          target_index = (int)way_point_array.size() - 1;

        if (target_index != path_index)
        {   
          path_index = target_index;
          goal_point = way_point_array[path_index];
          Flag_switch_goal = true;
        }

        double dist_to_goal = sqrt(
          pow(goal_point.pose.position.x - vehicleX, 2) +
          pow(goal_point.pose.position.y - vehicleY, 2) +
          pow(goal_point.pose.position.z - vehicleZ, 2));
        
        if (path_index == (int)way_point_array.size() - 1 && dist_to_goal < distance_tole)
        {
          Flag_finish_path = true;
        }
      }
    }

    if (Flag_switch_goal)
    {
      waypointMsgs.header.stamp = ros::Time().fromSec(curTime);
      waypointMsgs.point.x = goal_point.pose.position.x;
      waypointMsgs.point.y = goal_point.pose.position.y;
      waypointMsgs.point.z = goal_point.pose.position.z;
      pubWaypoint.publish(waypointMsgs);
      Flag_switch_goal = false;
    }

    rate.sleep();
  }

  return 0;
}
