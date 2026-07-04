#include <ros/ros.h>
#include <sensor_msgs/PointCloud2.h>
#include <tf/transform_listener.h>
#include <pcl_ros/transforms.h>
#include <pcl_conversions/pcl_conversions.h>
#include <pcl/point_types.h>
#include <pcl/point_cloud.h>

class CloudTransformer
{
public:
  CloudTransformer()
  {
    ros::NodeHandle private_nh("~");
    private_nh.param<std::string>("target_frame", target_frame_, "base_link");
    ROS_INFO("Target frame set to: %s", target_frame_.c_str());

    pub_ = nh_.advertise<sensor_msgs::PointCloud2>("/base_cloud", 1);
    sub_ = nh_.subscribe("/velodyne_points", 1, &CloudTransformer::cloudCallback, this);
  }

  void cloudCallback(const sensor_msgs::PointCloud2ConstPtr& cloud_msg)
  {
    sensor_msgs::PointCloud2 transformed_cloud;

    try
    {
      listener_.waitForTransform(target_frame_, cloud_msg->header.frame_id,
                                 cloud_msg->header.stamp, ros::Duration(1.0));
      pcl_ros::transformPointCloud(target_frame_, *cloud_msg, transformed_cloud, listener_);
      transformed_cloud.header.stamp = ros::Time::now();
      transformed_cloud.header.frame_id = target_frame_;

      sensor_msgs::PointCloud2 filtered_msg = filterPointCloud(transformed_cloud);
      pub_.publish(filtered_msg);
    }
    catch (tf::TransformException& ex)
    {
      ROS_WARN("Transform error: %s", ex.what());
    }
  }

  sensor_msgs::PointCloud2 filterPointCloud(const sensor_msgs::PointCloud2& input)
  {
    pcl::PointCloud<pcl::PointXYZ>::Ptr cloud(new pcl::PointCloud<pcl::PointXYZ>());
    pcl::fromROSMsg(input, *cloud);

    pcl::PointCloud<pcl::PointXYZ>::Ptr filtered(new pcl::PointCloud<pcl::PointXYZ>());
    for (const auto& pt : cloud->points)
    {
      float x = pt.x;
      float y = pt.y;
      float z = pt.z;


      // 过滤掉不在指定包围盒内的点
      if (x < -3.0 || x > 3.0) continue;    // 前后
      if (y < -3.0 || y > 3.0) continue;    // 左右
      if (z < -3.0 || z > 1.0) continue;    // 上下

      float distance = std::sqrt(x * x + y * y + z * z);

      // 过滤掉距离 base_link 原点小于 0.2m 的点
      if (distance < 0.2)
        continue;
      filtered->points.push_back(pt);
    }

    filtered->width = filtered->points.size();
    filtered->height = 1;
    filtered->is_dense = true;

    sensor_msgs::PointCloud2 output;
    pcl::toROSMsg(*filtered, output);
    output.header.stamp = ros::Time::now();
    output.header.frame_id = target_frame_;

    return output;
  }

private:
  ros::NodeHandle nh_;
  ros::Subscriber sub_;
  ros::Publisher pub_;
  tf::TransformListener listener_;
  std::string target_frame_;
};

int main(int argc, char** argv)
{
  ros::init(argc, argv, "cloud_transformer");
  CloudTransformer node;
  ros::spin();
  return 0;
}
