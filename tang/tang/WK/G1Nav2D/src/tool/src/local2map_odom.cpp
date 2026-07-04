#include <ros/ros.h>
#include <nav_msgs/Odometry.h>
#include <geometry_msgs/PoseStamped.h>
#include <tf/transform_listener.h>

class OdomTfConverter
{
public:
  OdomTfConverter()
  {
    tf_listener_ = std::make_shared<tf::TransformListener>();

    odom_sub_ = nh_.subscribe("/slam_odom", 10, &OdomTfConverter::odometryCallback, this);
    odom_pub_ = nh_.advertise<geometry_msgs::PoseStamped>("/odom_in_map", 10);
  }

  void odometryCallback(const nav_msgs::Odometry::ConstPtr& odom)
  {
    geometry_msgs::PoseStamped odom_pose;
    odom_pose.header = odom->header;
    odom_pose.pose = odom->pose.pose;

    geometry_msgs::PoseStamped map_pose;
    try
    {
      tf_listener_->transformPose("map", odom_pose, map_pose);

      ROS_INFO_STREAM("Transformed pose in 'map': "
                      << "x=" << map_pose.pose.position.x
                      << ", y=" << map_pose.pose.position.y
                      << ", z=" << map_pose.pose.position.z);

      odom_pub_.publish(map_pose);
    }
    catch (tf::TransformException& ex)
    {
      ROS_WARN("Transform from odom to map failed: %s", ex.what());
    }
  }

private:
  ros::NodeHandle nh_;
  ros::Subscriber odom_sub_;
  ros::Publisher odom_pub_;
  std::shared_ptr<tf::TransformListener> tf_listener_;
};

int main(int argc, char** argv)
{
  ros::init(argc, argv, "local2map_odom");
  OdomTfConverter converter;
  ros::spin();
  return 0;
}
