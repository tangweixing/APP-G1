#include <ros/ros.h>
#include <sensor_msgs/PointCloud2.h>
#include <tf/transform_listener.h>
#include <pcl_ros/transforms.h>

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
    sensor_msgs::PointCloud2 cloud_out;

    try
    {
      listener_.waitForTransform(target_frame_, cloud_msg->header.frame_id,
                                 cloud_msg->header.stamp, ros::Duration(1.0));
      pcl_ros::transformPointCloud(target_frame_, *cloud_msg, cloud_out, listener_);
      cloud_out.header.stamp = cloud_msg->header.stamp;
      cloud_out.header.frame_id = target_frame_;
      pub_.publish(cloud_out);
    }
    catch (tf::TransformException& ex)
    {
      ROS_WARN("Transform error: %s", ex.what());
    }
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
