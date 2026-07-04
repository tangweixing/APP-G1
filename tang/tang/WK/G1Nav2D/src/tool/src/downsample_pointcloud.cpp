#include <typeinfo>
#include "boost/range.hpp"
#include <ros/ros.h> 
#include <pcl/point_cloud.h> 
#include <pcl_conversions/pcl_conversions.h> 
#include <sensor_msgs/PointCloud2.h> 

#include <pcl/io/io.h>
#include <pcl/io/pcd_io.h>

#include <iostream>
#include <vector>
#include <ctime>

#include <pcl/filters/voxel_grid.h>
#include <pcl/PCLPointCloud2.h>
#include <pcl/conversions.h>
#include <pcl_conversions/pcl_conversions.h>
#include <pcl/point_types_conversion.h>

int main(int argc, char **argv) 
{ 
    ros::init(argc, argv, "pcl_create"); 

    ros::NodeHandle nh; 
    
    // 获取参数，设置默认值
    std::string pcd_file;
    std::string output_topic;
    float voxel_size;

    nh.param<std::string>("pcd_file", pcd_file, "/home/zjh/cloud_test/table_scene_lms400.pcd");  // 默认路径
    nh.param<std::string>("output_topic", output_topic, "pcl_output");  // 默认输出话题
    nh.param<float>("voxel_size", voxel_size, 0.03f);  // 默认体素大小

    // 创建发布者
    ros::Publisher pcl_pub = nh.advertise<sensor_msgs::PointCloud2>(output_topic, 1);  

    // 创建带强度信息的 PointCloud 对象
    pcl::PointCloud<pcl::PointXYZI>::Ptr cloud2(new pcl::PointCloud<pcl::PointXYZI>);
    pcl::PointCloud<pcl::PointXYZI>::Ptr cloud_filtered(new pcl::PointCloud<pcl::PointXYZI>);  
    pcl::PCLPointCloud2 cloud;
    sensor_msgs::PointCloud2 output;

    // 加载 PCD 文件
    if (pcl::io::loadPCDFile(pcd_file, cloud) == -1) {
        PCL_ERROR("Couldn't read file %s\n", pcd_file.c_str());
        return -1;
    }

    // 转换为 PointCloud<pcl::PointXYZI>
    pcl::fromPCLPointCloud2(cloud, *cloud2);
    std::cout << "Loaded " << cloud2->width * cloud2->height << " points from file: " << pcd_file << std::endl;

    // 创建体素网格过滤器并应用
    pcl::VoxelGrid<pcl::PointXYZI> sor;
    sor.setInputCloud(cloud2);
    sor.setLeafSize(voxel_size, voxel_size, voxel_size);  // 使用传入的体素大小
    sor.filter(*cloud_filtered);
    
    std::cerr << "PointCloud after filtering: " << cloud_filtered->width * cloud_filtered->height 
              << " data points (" << pcl::getFieldsList(*cloud_filtered) << ")." << std::endl;
    
    // 将降采样后的点云转换为 ROS 消息
    pcl::toROSMsg(*cloud_filtered, output);
    output.header.frame_id = "map";  // 设置坐标系，视情况而定

    ros::Rate loop_rate(1);  // 设置发布频率

    while (ros::ok()) { 
        pcl_pub.publish(output);
        ros::spinOnce(); 
        loop_rate.sleep(); 
    } 
    
    return 0;
}
