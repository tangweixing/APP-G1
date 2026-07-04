#include <ros/ros.h>
#include <sensor_msgs/PointCloud2.h>
#include <tf/transform_listener.h>
#include <pcl_ros/transforms.h>
#include <pcl_conversions/pcl_conversions.h>
#include <pcl/point_cloud.h>
#include <pcl/point_types.h>
#include <pcl/filters/passthrough.h>
#include <pcl/filters/crop_box.h>
#include <pcl/common/common.h>
#include <pcl/kdtree/kdtree_flann.h>
#include <geometry_msgs/PointStamped.h>

// 融合帧结构
struct FusedFrame {
  pcl::PointCloud<pcl::PointXYZI>::Ptr cloud;
  pcl::PointCloud<pcl::PointXYZI>::Ptr original_cloud;
  geometry_msgs::Point position;
  ros::Time timestamp;
  
  FusedFrame() {
    cloud.reset(new pcl::PointCloud<pcl::PointXYZI>);
    original_cloud.reset(new pcl::PointCloud<pcl::PointXYZI>);
  }
};

class CloudTransformer
{
public:
  CloudTransformer()
  {
    ros::NodeHandle private_nh("~");

    // 初始化发布者
    pub_ = nh_.advertise<sensor_msgs::PointCloud2>("/map_cloud", 1);
    pub_original_ = nh_.advertise<sensor_msgs::PointCloud2>("/map_cloud_original", 1);

    // 初始化订阅者
    sub_ = nh_.subscribe("/velodyne_points", 1, &CloudTransformer::cloudCallback, this);
    
    // 初始化融合参数
    position_threshold_ = 0.3;  // 位置变化阈值0.3m
    spatial_range_ = 1.5;  // 空间管理范围1.5m (用于融合帧移除和当前帧过滤)
    removal_time_threshold_ = 3;  // 融合帧移除时间阈值1.5s
    
    // 初始化上次融合位置
    last_fused_position_.x = std::numeric_limits<double>::max();
    last_fused_position_.y = std::numeric_limits<double>::max();
    last_fused_position_.z = std::numeric_limits<double>::max();
  }

  void cloudCallback(const sensor_msgs::PointCloud2ConstPtr& cloud_msg)
  {
    sensor_msgs::PointCloud2 cloud_out;

    try
    {
      // 获取当前机器人位置
      geometry_msgs::Point current_position;
      if (!getCurrentRobotPosition(current_position, cloud_msg->header.stamp))
      {
        ROS_WARN("Failed to get robot position");
        return;
      }

      // 等待变换（源 -> 目标坐标系）
      listener_.waitForTransform( "base_link", cloud_msg->header.frame_id,
                                 cloud_msg->header.stamp, ros::Duration(5.0));

      // 执行变换到目标坐标系
      pcl_ros::transformPointCloud( "base_link", *cloud_msg, cloud_out, listener_);

      // 转换为PCL格式进行处理
      pcl::PointCloud<pcl::PointXYZI>::Ptr cloud_pcl(new pcl::PointCloud<pcl::PointXYZI>);
      pcl::fromROSMsg(cloud_out, *cloud_pcl);

      // 1. 距离滤波：仅保留5m范围内的点
      pcl::PointCloud<pcl::PointXYZI>::Ptr range_filtered_cloud(new pcl::PointCloud<pcl::PointXYZI>);
      for (const auto& point : cloud_pcl->points)
      {
        double distance = std::sqrt(point.x * point.x + point.y * point.y);
        if (distance <= 5.0)
        {
          if(!(point.x <= 0.15 && point.x >= -0.15 && point.y >= -0.2 && point.y <= 0.2))
          {
          range_filtered_cloud->points.push_back(point);
          }
        }
      }
      range_filtered_cloud->width = range_filtered_cloud->points.size();
      range_filtered_cloud->height = 1;
      range_filtered_cloud->is_dense = true;
      range_filtered_cloud->header = cloud_pcl->header;

      // 2. Z轴滤波：保留-0.2到0.15范围内的点
      pcl::PointCloud<pcl::PointXYZI>::Ptr filtered_cloud(new pcl::PointCloud<pcl::PointXYZI>);
      pcl::PassThrough<pcl::PointXYZI> pass_filter;
      pass_filter.setInputCloud(range_filtered_cloud);
      pass_filter.setFilterFieldName("z");
      pass_filter.setFilterLimits(-1, 0.15);
      pass_filter.filter(*filtered_cloud);

      // 3. 将所有点的Z坐标映射到+0.6m高度
      for (auto& point : filtered_cloud->points)
      {
        point.z = 0.6;
      }

      // 转换当前帧到map坐标系
      sensor_msgs::PointCloud2 current_cloud_msg;
      pcl::toROSMsg(*filtered_cloud, current_cloud_msg);
      current_cloud_msg.header.stamp = cloud_msg->header.stamp;
      current_cloud_msg.header.frame_id = "base_link";
      
      sensor_msgs::PointCloud2 current_map_cloud_msg;
      listener_.waitForTransform("map", "base_link",
                                 cloud_msg->header.stamp, ros::Duration(5.0));
      pcl_ros::transformPointCloud("map", current_cloud_msg, current_map_cloud_msg, listener_);
      
      pcl::PointCloud<pcl::PointXYZI>::Ptr current_map_pcl(new pcl::PointCloud<pcl::PointXYZI>);
      pcl::fromROSMsg(current_map_cloud_msg, *current_map_pcl);

      // 4. 在XY平面进行膨胀
      pcl::PointCloud<pcl::PointXYZI>::Ptr dilated_cloud(new pcl::PointCloud<pcl::PointXYZI>);
      dilatePointCloudXY(filtered_cloud, dilated_cloud, 0.3);

      // 转换膨胀后的点云到map坐标系
      sensor_msgs::PointCloud2 dilated_cloud_msg;
      pcl::toROSMsg(*dilated_cloud, dilated_cloud_msg);
      dilated_cloud_msg.header.stamp = cloud_msg->header.stamp;
      dilated_cloud_msg.header.frame_id = "base_link";
      
      sensor_msgs::PointCloud2 dilated_map_cloud_msg;
      pcl_ros::transformPointCloud("map", dilated_cloud_msg, dilated_map_cloud_msg, listener_);
      
      pcl::PointCloud<pcl::PointXYZI>::Ptr dilated_map_pcl(new pcl::PointCloud<pcl::PointXYZI>);
      pcl::fromROSMsg(dilated_map_cloud_msg, *dilated_map_pcl);

      // 融合点云管理
      manageFusedFrames(current_position, cloud_msg->header.stamp, current_map_pcl, dilated_map_pcl);
      
      // 发布融合结果
      publishFusedClouds(cloud_msg->header.stamp);
    }
    catch (tf::TransformException& ex)
    {
      ROS_WARN("Transform error: %s", ex.what());
    }
  }

  // XY平面膨胀函数
  void dilatePointCloudXY(const pcl::PointCloud<pcl::PointXYZI>::Ptr& input_cloud,
                          pcl::PointCloud<pcl::PointXYZI>::Ptr& output_cloud,
                          double dilation_radius)
  {
    if (input_cloud->empty())
    {
      *output_cloud = *input_cloud;
      return;
    }

    // 使用网格方法进行膨胀
    double grid_resolution = 0.05; // 5cm网格分辨率
    std::map<std::pair<int, int>, bool> occupied_grid;
    
    // 将原始点投影到网格
    for (const auto& point : input_cloud->points)
    {
      int grid_x = static_cast<int>(std::round(point.x / grid_resolution));
      int grid_y = static_cast<int>(std::round(point.y / grid_resolution));
      occupied_grid[{grid_x, grid_y}] = true;
    }
    
    // 计算膨胀半径对应的网格数
    int dilation_grid_radius = static_cast<int>(std::ceil(dilation_radius / grid_resolution));
    
    // 执行膨胀操作
    std::map<std::pair<int, int>, bool> dilated_grid = occupied_grid;
    for (const auto& cell : occupied_grid)
    {
      int center_x = cell.first.first;
      int center_y = cell.first.second;
      
      // 在膨胀半径内添加点
      for (int dx = -dilation_grid_radius; dx <= dilation_grid_radius; ++dx)
      {
        for (int dy = -dilation_grid_radius; dy <= dilation_grid_radius; ++dy)
        {
          double dist = std::sqrt(dx * dx + dy * dy) * grid_resolution;
          if (dist <= dilation_radius)
          {
            dilated_grid[{center_x + dx, center_y + dy}] = true;
          }
        }
      }
    }
    
    // 将膨胀后的网格转换回点云
    output_cloud->clear();
    output_cloud->header = input_cloud->header;
    
    for (const auto& cell : dilated_grid)
    {
      pcl::PointXYZI point;
      point.x = cell.first.first * grid_resolution;
      point.y = cell.first.second * grid_resolution;
      point.z = 0.6; // 固定高度
      point.intensity = 1.0;
      output_cloud->points.push_back(point);
    }
    
    output_cloud->width = output_cloud->points.size();
    output_cloud->height = 1;
    output_cloud->is_dense = true;
  }

  // 获取当前机器人在map坐标系中的位置
  bool getCurrentRobotPosition(geometry_msgs::Point& position, const ros::Time& timestamp)
  {
    try
    {
      listener_.waitForTransform("map", "base_link", timestamp, ros::Duration(1.0));
      tf::StampedTransform transform;
      listener_.lookupTransform("map", "base_link", timestamp, transform);
      
      position.x = transform.getOrigin().x();
      position.y = transform.getOrigin().y();
      position.z = transform.getOrigin().z();
      return true;
    }
    catch (tf::TransformException& ex)
    {
      ROS_WARN("Failed to get robot position: %s", ex.what());
      return false;
    }
  }

  // 计算两个位置之间的距离
  double calculateDistance(const geometry_msgs::Point& p1, const geometry_msgs::Point& p2)
  {
    double dx = p1.x - p2.x;
    double dy = p1.y - p2.y;
    double dz = p1.z - p2.z;
    return std::sqrt(dx*dx + dy*dy + dz*dz);
  }

  // 管理融合帧
  void manageFusedFrames(const geometry_msgs::Point& current_position, 
                        const ros::Time& current_time,
                        const pcl::PointCloud<pcl::PointXYZI>::Ptr& current_original,
                        const pcl::PointCloud<pcl::PointXYZI>::Ptr& current_processed)
  {
    // 检查是否需要创建新的融合帧
    bool should_create_new_frame = false;
    
    if (last_fused_position_.x == std::numeric_limits<double>::max())
    {
      // 第一帧
      should_create_new_frame = true;
    }
    else
    {
      double distance_to_last = calculateDistance(current_position, last_fused_position_);
      if (distance_to_last > position_threshold_)
      {
        should_create_new_frame = true;
      }
    }

    if (should_create_new_frame)
    {
      // 创建新的融合帧
      FusedFrame new_frame;
      *new_frame.original_cloud = *current_original;
      *new_frame.cloud = *current_processed;
      new_frame.position = current_position;
      new_frame.timestamp = current_time;
      
      fused_frames_.push_back(new_frame);
      last_fused_position_ = current_position;
    }

    // 移除过时的融合帧
    auto it = fused_frames_.begin();
    while (it != fused_frames_.end())
    {
      double distance = calculateDistance(current_position, it->position);
      double time_diff = (current_time - it->timestamp).toSec();
      
      if (distance > spatial_range_ || time_diff > removal_time_threshold_)
      {
        it = fused_frames_.erase(it);
      }
      else
      {
        ++it;
      }
    }

    // 保存当前帧
    current_frame_original_ = current_original;
    current_frame_processed_ = current_processed;
    current_position_ = current_position;
  }

  // 发布融合后的点云
  void publishFusedClouds(const ros::Time& timestamp)
  {
    // 创建融合点云
    pcl::PointCloud<pcl::PointXYZI>::Ptr fused_original(new pcl::PointCloud<pcl::PointXYZI>);
    pcl::PointCloud<pcl::PointXYZI>::Ptr fused_processed(new pcl::PointCloud<pcl::PointXYZI>);

    // 添加当前帧
    if (current_frame_original_)
    {
      // 过滤当前帧，只保留机器人spatial_range_范围内的点
      filterPointsByDistance(current_frame_original_, fused_original, current_position_, spatial_range_);
      filterPointsByDistance(current_frame_processed_, fused_processed, current_position_, spatial_range_);
    }

    // 添加所有融合帧，但需要过滤掉机器人前方x>0.4m的区域
    for (const auto& frame : fused_frames_)
    {
      // 为融合帧创建临时点云，过滤掉机器人前方x>0.4m的点
      pcl::PointCloud<pcl::PointXYZI>::Ptr filtered_original(new pcl::PointCloud<pcl::PointXYZI>);
      pcl::PointCloud<pcl::PointXYZI>::Ptr filtered_processed(new pcl::PointCloud<pcl::PointXYZI>);
      
      filterPointsExcludingFrontArea(frame.original_cloud, filtered_original, current_position_, 0.4);
      filterPointsExcludingFrontArea(frame.cloud, filtered_processed, current_position_, 0.4);
      
      *fused_original += *filtered_original;
      *fused_processed += *filtered_processed;
    }

    // 发布原始点云
    if (!fused_original->empty())
    {
      sensor_msgs::PointCloud2 original_msg;
      pcl::toROSMsg(*fused_original, original_msg);
      original_msg.header.stamp = timestamp;
      original_msg.header.frame_id = "map";
      pub_original_.publish(original_msg);
    }

    // 发布处理后的点云
    if (!fused_processed->empty())
    {
      sensor_msgs::PointCloud2 processed_msg;
      pcl::toROSMsg(*fused_processed, processed_msg);
      processed_msg.header.stamp = timestamp;
      processed_msg.header.frame_id = "map";
      pub_.publish(processed_msg);
    }
  }

  // 根据距离过滤点云
  void filterPointsByDistance(const pcl::PointCloud<pcl::PointXYZI>::Ptr& input_cloud,
                             pcl::PointCloud<pcl::PointXYZI>::Ptr& output_cloud,
                             const geometry_msgs::Point& center_position,
                             double max_distance)
  {
    output_cloud->clear();
    output_cloud->header = input_cloud->header;
    
    for (const auto& point : input_cloud->points)
    {
      double dx = point.x - center_position.x;
      double dy = point.y - center_position.y;
      double distance = std::sqrt(dx*dx + dy*dy);
      
      if (distance <= max_distance)
      {
        output_cloud->points.push_back(point);
      }
    }
    
    output_cloud->width = output_cloud->points.size();
    output_cloud->height = 1;
    output_cloud->is_dense = true;
  }

  // 过滤点云，排除机器人前方指定距离内的点
  void filterPointsExcludingFrontArea(const pcl::PointCloud<pcl::PointXYZI>::Ptr& input_cloud,
                                     pcl::PointCloud<pcl::PointXYZI>::Ptr& output_cloud,
                                     const geometry_msgs::Point& robot_position,
                                     double front_exclusion_distance)
  {
    output_cloud->clear();
    output_cloud->header = input_cloud->header;
    
    // 获取机器人当前朝向（从tf获取）
    tf::StampedTransform robot_transform;
    try
    {
      listener_.lookupTransform("map", "base_link", ros::Time(0), robot_transform);
      
      // 计算机器人朝向向量（x轴正方向在机器人坐标系中）
      tf::Vector3 front_direction = robot_transform.getBasis() * tf::Vector3(1, 0, 0);
      
      for (const auto& point : input_cloud->points)
      {
        // 计算点相对于机器人的向量
        double dx = point.x - robot_position.x;
        double dy = point.y - robot_position.y;
        
        // 计算点在机器人前方向上的投影距离
        double front_projection = dx * front_direction.x() + dy * front_direction.y();
        
        // 如果点不在机器人前方exclusion_distance距离内，则保留
        if (front_projection <= front_exclusion_distance)
        {
          output_cloud->points.push_back(point);
        }
      }
    }
    catch (tf::TransformException& ex)
    {
      ROS_WARN("Failed to get robot orientation for front area filtering: %s", ex.what());
      // 如果获取朝向失败，则保留所有点
      *output_cloud = *input_cloud;
      return;
    }
    
    output_cloud->width = output_cloud->points.size();
    output_cloud->height = 1;
    output_cloud->is_dense = true;
  }

private:
  ros::NodeHandle nh_;
  ros::Subscriber sub_;
  ros::Publisher pub_;
  ros::Publisher pub_original_;
  tf::TransformListener listener_;
  
  // 融合帧管理
  std::vector<FusedFrame> fused_frames_;
  geometry_msgs::Point last_fused_position_;
  geometry_msgs::Point current_position_;
  
  // 当前帧点云
  pcl::PointCloud<pcl::PointXYZI>::Ptr current_frame_original_;
  pcl::PointCloud<pcl::PointXYZI>::Ptr current_frame_processed_;
  
  // 融合参数
  double position_threshold_;        // 位置变化阈值
  double spatial_range_;            // 空间管理范围(融合帧移除距离和当前帧保留范围)
  double removal_time_threshold_;    // 融合帧移除时间阈值

  // std::string target_frame_;
};

int main(int argc, char** argv)
{
  ros::init(argc, argv, "cloud_transformer");
  CloudTransformer node;
  ros::spin();
  return 0;
}
