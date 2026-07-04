#include "ros_map_edit/map_file_manager.h"
#include <fstream>
#include <sstream>
#include <iostream>
#include <yaml-cpp/yaml.h>
#include <ros/ros.h>
#include <visualization_msgs/MarkerArray.h>

namespace ros_map_edit
{

MapFileManager::MapFileManager()
{
}

MapFileManager::~MapFileManager()
{
}

bool MapFileManager::loadVirtualWalls(const std::string& filename, std::vector<VirtualWall>& walls)
{
  try
  {
    std::ifstream file(filename);
    if (!file.is_open())
    {
      last_error_ = "Failed to open file: " + filename;
      return false;
    }

    Json::Value root;
    file >> root;

    walls.clear();
    
    if (root.isMember("vws") && root["vws"].isArray())
    {
      for (const auto& vw_json : root["vws"])
      {
        if (vw_json.isMember("points") && vw_json["points"].isArray())
        {
          VirtualWall wall;
          wall.id = "wall_" + std::to_string(walls.size());
          
          for (const auto& point_json : vw_json["points"])
          {
            geometry_msgs::Point point = jsonToPoint(point_json);
            wall.points.push_back(point);
          }
          
          if (wall.points.size() >= 2)
          {
            walls.push_back(wall);
          }
        }
      }
    }

    return true;
  }
  catch (const std::exception& e)
  {
    last_error_ = "Error parsing JSON: " + std::string(e.what());
    return false;
  }
}

bool MapFileManager::saveVirtualWalls(const std::string& filename, const std::vector<VirtualWall>& walls)
{
  try
  {
    Json::Value root;
    Json::Value vws_array(Json::arrayValue);

    for (const auto& wall : walls)
    {
      if (wall.points.size() >= 2)
      {
        Json::Value wall_json;
        Json::Value points_array(Json::arrayValue);
        
        for (const auto& point : wall.points)
        {
          points_array.append(pointToJson(point));
        }
        
        wall_json["points"] = points_array;
        vws_array.append(wall_json);
      }
    }

    root["vws"] = vws_array;

    std::ofstream file(filename);
    if (!file.is_open())
    {
      last_error_ = "Failed to create file: " + filename;
      return false;
    }

    Json::StreamWriterBuilder builder;
    builder["indentation"] = "   ";
    std::unique_ptr<Json::StreamWriter> writer(builder.newStreamWriter());
    writer->write(root, &file);
    
    return true;
  }
  catch (const std::exception& e)
  {
    last_error_ = "Error writing JSON: " + std::string(e.what());
    return false;
  }
}

bool MapFileManager::loadRegions(const std::string& filename, std::vector<Region>& regions)
{
  try
  {
    std::ifstream file(filename);
    if (!file.is_open())
    {
      last_error_ = "Failed to open file: " + filename;
      return false;
    }

    Json::Value root;
    file >> root;

    regions.clear();
    
    if (root.isMember("regions") && root["regions"].isArray())
    {
      for (const auto& region_json : root["regions"])
      {
        Region region;
        region.id = region_json["id"].asString();
        region.frame_id = region_json["frame_id"].asString();
        region.type = region_json["type"].asInt();
        region.param = region_json["param"].asDouble();
        
        if (region_json.isMember("points") && region_json["points"].isArray())
        {
          for (const auto& point_json : region_json["points"])
          {
            geometry_msgs::Point point = jsonToPoint(point_json);
            region.points.push_back(point);
          }
          
          if (region.points.size() >= 3)
          {
            regions.push_back(region);
          }
        }
      }
    }

    return true;
  }
  catch (const std::exception& e)
  {
    last_error_ = "Error parsing JSON: " + std::string(e.what());
    return false;
  }
}

bool MapFileManager::saveRegions(const std::string& filename, const std::vector<Region>& regions)
{
  try
  {
    Json::Value root;
    Json::Value regions_array(Json::arrayValue);

    for (const auto& region : regions)
    {
      if (region.points.size() >= 3)
      {
        Json::Value region_json;
        region_json["id"] = region.id;
        region_json["frame_id"] = region.frame_id;
        region_json["type"] = region.type;
        region_json["param"] = region.param;
        
        Json::Value points_array(Json::arrayValue);
        for (const auto& point : region.points)
        {
          points_array.append(pointToJson(point));
        }
        
        region_json["points"] = points_array;
        regions_array.append(region_json);
      }
    }

    root["regions"] = regions_array;

    std::ofstream file(filename);
    if (!file.is_open())
    {
      last_error_ = "Failed to create file: " + filename;
      return false;
    }

    Json::StreamWriterBuilder builder;
    builder["indentation"] = "  ";
    std::unique_ptr<Json::StreamWriter> writer(builder.newStreamWriter());
    writer->write(root, &file);
    
    return true;
  }
  catch (const std::exception& e)
  {
    last_error_ = "Error writing JSON: " + std::string(e.what());
    return false;
  }
}

bool MapFileManager::loadMap(const std::string& filename, nav_msgs::OccupancyGrid& map)
{
  // Determine file type from extension
  std::string ext = filename.substr(filename.find_last_of(".") + 1);
  
  if (ext == "yaml" || ext == "yml")
  {
    return loadYAML(filename, map);
  }
  else if (ext == "pgm")
  {
    return loadPGM(filename, map);
  }
  else
  {
    last_error_ = "Unsupported file format: " + ext;
    return false;
  }
}

bool MapFileManager::saveMap(const std::string& filename, const nav_msgs::OccupancyGrid& map)
{
  // Determine file type from extension
  std::string ext = filename.substr(filename.find_last_of(".") + 1);
  
  if (ext == "yaml" || ext == "yml")
  {
    return saveYAML(filename, map);
  }
  else if (ext == "pgm")
  {
    return savePGM(filename, map);
  }
  else
  {
    last_error_ = "Unsupported file format: " + ext;
    return false;
  }
}

bool MapFileManager::saveMapImage(const std::string& filename, const nav_msgs::OccupancyGrid& map)
{
  return savePGM(filename, map);
}

bool MapFileManager::saveMapFiles(const std::string& yaml_filename)
{
  // 尝试从map_edited话题获取当前编辑的地图
  ros::NodeHandle nh;
  nav_msgs::OccupancyGridConstPtr map_msg = 
    ros::topic::waitForMessage<nav_msgs::OccupancyGrid>("map_edited", nh, ros::Duration(1.0));
  
  if (!map_msg)
  {
    // 如果没有编辑后的地图，尝试获取原始地图
    map_msg = ros::topic::waitForMessage<nav_msgs::OccupancyGrid>("map", nh, ros::Duration(5.0));
    
    if (!map_msg)
    {
      last_error_ = "无法获取地图数据，请确保地图话题正在发布";
      return false;
    }
  }
  
  return saveYAML(yaml_filename, *map_msg);
}

bool MapFileManager::saveMapFiles(const std::string& yaml_filename, const nav_msgs::OccupancyGrid& map)
{
  // 直接保存传入的地图数据
  return saveYAML(yaml_filename, map);
}

bool MapFileManager::saveVirtualWallsFile(const std::string& filename)
{
  // 尝试从虚拟墙话题获取数据
  ros::NodeHandle nh;
  visualization_msgs::MarkerArrayConstPtr walls_msg = 
    ros::topic::waitForMessage<visualization_msgs::MarkerArray>("virtual_walls_markers", nh, ros::Duration(1.0));
  
  // 创建基本的空文件结构
  Json::Value root;
  root["vws"] = Json::Value(Json::arrayValue);
  
  if (walls_msg && !walls_msg->markers.empty())
  {
    // 转换MarkerArray到VirtualWall格式
    std::vector<VirtualWall> walls;
    
    for (const auto& marker : walls_msg->markers)
    {
      if (marker.type == visualization_msgs::Marker::LINE_STRIP && 
          marker.points.size() >= 2)
      {
        VirtualWall current_wall;
        current_wall.points.clear();
        for (const auto& point : marker.points)
        {
          geometry_msgs::Point p;
          p.x = point.x;
          p.y = point.y;
          p.z = point.z;
          current_wall.points.push_back(p);
        }
        current_wall.id = "wall_" + std::to_string(marker.id);
        walls.push_back(current_wall);
      }
    }
    
    return saveVirtualWalls(filename, walls);
  }
  
  // 保存空文件
  std::ofstream file(filename);
  if (!file.is_open())
  {
    last_error_ = "Failed to create virtual walls file: " + filename;
    return false;
  }

  Json::StreamWriterBuilder builder;
  builder["indentation"] = "   ";
  std::unique_ptr<Json::StreamWriter> writer(builder.newStreamWriter());
  writer->write(root, &file);
  
  return true;
}

bool MapFileManager::saveVirtualWallsFile(const std::string& filename, const std::vector<VirtualWall>& walls)
{
  // 直接保存传入的虚拟墙数据
  return saveVirtualWalls(filename, walls);
}

bool MapFileManager::saveRegionsFile(const std::string& filename)
{
  // 尝试从区域话题获取数据
  ros::NodeHandle nh;
  visualization_msgs::MarkerArrayConstPtr regions_msg = 
    ros::topic::waitForMessage<visualization_msgs::MarkerArray>("region_markers", nh, ros::Duration(1.0));
  
  // 创建基本的空文件结构
  Json::Value root;
  root["regions"] = Json::Value(Json::arrayValue);
  
  if (regions_msg && !regions_msg->markers.empty())
  {
    // 转换MarkerArray到Region格式
    std::vector<Region> regions;
    
    for (const auto& marker : regions_msg->markers)
    {
      if (marker.type == visualization_msgs::Marker::TRIANGLE_LIST && 
          marker.points.size() >= 3)
      {
        Region region;
        region.id = "region_" + std::to_string(marker.id);
        region.frame_id = marker.header.frame_id;
        region.type = 0;
        region.param = 1.0;
        
        // 从三角形列表重构多边形（简化处理）
        std::set<std::pair<double, double>> unique_points;
        for (const auto& point : marker.points)
        {
          unique_points.insert({point.x, point.y});
        }
        
        for (const auto& unique_point : unique_points)
        {
          geometry_msgs::Point p;
          p.x = unique_point.first;
          p.y = unique_point.second;
          p.z = 0.0;
          region.points.push_back(p);
        }
        
        regions.push_back(region);
      }
    }
    
    return saveRegions(filename, regions);
  }
  
  // 保存空文件
  std::ofstream file(filename);
  if (!file.is_open())
  {
    last_error_ = "Failed to create regions file: " + filename;
    return false;
  }

  Json::StreamWriterBuilder builder;
  builder["indentation"] = "  ";
  std::unique_ptr<Json::StreamWriter> writer(builder.newStreamWriter());
  writer->write(root, &file);
  
  return true;
}

bool MapFileManager::saveRegionsFile(const std::string& filename, const std::vector<Region>& regions)
{
  // 直接保存传入的区域数据
  return saveRegions(filename, regions);
}

Json::Value MapFileManager::pointToJson(const geometry_msgs::Point& point)
{
  Json::Value json;
  json["x"] = point.x;
  json["y"] = point.y;
  json["z"] = point.z;
  return json;
}

geometry_msgs::Point MapFileManager::jsonToPoint(const Json::Value& json)
{
  geometry_msgs::Point point;
  point.x = json["x"].asDouble();
  point.y = json["y"].asDouble();
  point.z = json.isMember("z") ? json["z"].asDouble() : 0.0;
  return point;
}

bool MapFileManager::loadPGMWithParams(const std::string& filename, nav_msgs::OccupancyGrid& map,
                                     double occupied_thresh, double free_thresh, bool negate)
{
  std::ifstream file(filename, std::ios::binary);
  if (!file.is_open())
  {
    last_error_ = "Failed to open PGM file: " + filename;
    return false;
  }

  std::string format;
  int width, height, maxval;
  
  // 读取PGM文件头
  file >> format;
  if (format != "P5")
  {
    last_error_ = "Only P5 PGM format is supported";
    return false;
  }
  
  // 跳过注释行
  std::string line;
  std::getline(file, line); // 跳过format行的剩余部分
  while (std::getline(file, line) && line[0] == '#') {
    // 跳过注释行
  }
  
  // 解析宽度和高度（可能在同一行或不同行）
  std::istringstream iss(line);
  if (!(iss >> width)) {
    last_error_ = "Failed to read width from PGM file";
    return false;
  }
  
  if (!(iss >> height)) {
    // 如果高度不在同一行，读取下一行
    if (!std::getline(file, line) || !(std::istringstream(line) >> height)) {
      last_error_ = "Failed to read height from PGM file";
      return false;
    }
  }
  
  // 读取最大值
  file >> maxval;
  if (maxval != 255) {
    last_error_ = "Only 8-bit PGM files (maxval 255) are supported";
    return false;
  }
  
  file.ignore(1); // 跳过最后一个换行符
  
  // 设置地图信息
  map.info.width = width;
  map.info.height = height;
  // 如果resolution还未设置（即为0），设置默认值
  if (map.info.resolution == 0.0) {
    map.info.resolution = 0.05; // 默认分辨率，通常由YAML文件提供
    map.info.origin.position.x = 0.0;
    map.info.origin.position.y = 0.0;
    map.info.origin.position.z = 0.0;
    map.info.origin.orientation.w = 1.0;
  }
  
  map.data.resize(width * height);
  
  // 读取图像数据
  std::vector<uint8_t> image_data(width * height);
  file.read(reinterpret_cast<char*>(image_data.data()), width * height);
  
  if (!file) {
    last_error_ = "Failed to read image data from PGM file";
    return false;
  }
  
  // 根据ROS map_server的标准转换PGM数据到占用栅格
  // 参考ROS wiki: http://wiki.ros.org/map_server#Value_Interpretation
  for (int i = 0; i < width * height; ++i)
  {
    uint8_t pixel = image_data[i];
    
    // 转换像素值到概率 (根据negate标志)
    double p;
    if (negate) {
      p = pixel / 255.0;
    } else {
      p = (255 - pixel) / 255.0;
    }
    
    // 根据阈值转换为占用栅格值
    if (p > occupied_thresh) {
      map.data[i] = 100;  // 占用
    } else if (p < free_thresh) {
      map.data[i] = 0;    // 自由
    } else {
      map.data[i] = -1;   // 未知
    }
  }
  
  return true;
}

bool MapFileManager::loadPGM(const std::string& filename, nav_msgs::OccupancyGrid& map)
{
  // 使用默认参数调用带参数的版本
  return loadPGMWithParams(filename, map, 0.65, 0.196, false);
}

bool MapFileManager::savePGM(const std::string& filename, const nav_msgs::OccupancyGrid& map)
{
  std::ofstream file(filename, std::ios::binary);
  if (!file.is_open())
  {
    last_error_ = "Failed to create PGM file: " + filename;
    return false;
  }

  // 写入PGM文件头
  file << "P5\n";
  file << "# Created by ros_map_edit\n";
  file << map.info.width << " " << map.info.height << "\n";
  file << "255\n";
  
  // 准备图像数据
  std::vector<uint8_t> image_data(map.info.width * map.info.height);
  
  // 根据ROS map_server的标准转换占用栅格到PGM数据
  const double occupied_thresh = 0.65;
  const double free_thresh = 0.196;
  const bool negate = false;
  
  for (size_t i = 0; i < map.data.size(); ++i)
  {
    int8_t cell = map.data[i];
    uint8_t pixel;
    
    if (cell == 0) {
      // 自由空间 -> 根据negate转换
      pixel = negate ? 0 : 254;
    } else if (cell == 100) {
      // 占用空间 -> 根据negate转换  
      pixel = negate ? 254 : 0;
    } else {
      // 未知空间 -> 灰色
      pixel = 205;
    }
    
    image_data[i] = pixel;
  }
  
  // 写入图像数据
  file.write(reinterpret_cast<char*>(image_data.data()), image_data.size());
  
  if (!file) {
    last_error_ = "Failed to write image data to PGM file";
    return false;
  }
  
  return true;
}

bool MapFileManager::loadYAML(const std::string& filename, nav_msgs::OccupancyGrid& map)
{
  try
  {
    ROS_INFO("正在解析YAML文件: %s", filename.c_str());
    YAML::Node config = YAML::LoadFile(filename);
    
    // 解析地图参数
    map.info.resolution = config["resolution"].as<double>();
    
    // 解析origin数组
    if (config["origin"] && config["origin"].IsSequence() && config["origin"].size() >= 2)
    {
      map.info.origin.position.x = config["origin"][0].as<double>();
      map.info.origin.position.y = config["origin"][1].as<double>();
      map.info.origin.position.z = 0.0;
      map.info.origin.orientation.w = 1.0;
    }
    else
    {
      last_error_ = "Invalid or missing origin field in YAML file";
      return false;
    }
    
    // 解析PGM解释参数，使用默认值如果不存在
    double occupied_thresh = 0.65;
    double free_thresh = 0.196;
    bool negate = false;
    
    if (config["occupied_thresh"].IsDefined())
    {
      occupied_thresh = config["occupied_thresh"].as<double>();
    }
    
    if (config["free_thresh"].IsDefined())
    {
      free_thresh = config["free_thresh"].as<double>();
    }
    
    if (config["negate"].IsDefined())
    {
      // negate字段可能是布尔值或整数，需要兼容处理
      try {
        negate = config["negate"].as<bool>();
      } catch (const YAML::BadConversion&) {
        // 如果无法转换为布尔值，尝试作为整数处理
        int negate_int = config["negate"].as<int>();
        negate = (negate_int != 0);
      }
    }
    
    ROS_INFO("YAML解析成功 - 分辨率: %.3f, 原点: [%.2f, %.2f], occupied_thresh: %.3f, free_thresh: %.3f, negate: %s", 
             map.info.resolution, map.info.origin.position.x, map.info.origin.position.y,
             occupied_thresh, free_thresh, negate ? "true" : "false");
    
    // 获取图像文件名
    if (!config["image"].IsDefined())
    {
      last_error_ = "Missing image field in YAML file";
      return false;
    }
    
    std::string image_file = config["image"].as<std::string>();
    ROS_INFO("YAML中指定的图像文件: %s", image_file.c_str());
    
    // 构建PGM文件的完整路径
    std::string pgm_filename;
    
    // 如果image_file是绝对路径，直接使用
    if (image_file[0] == '/' || (image_file.size() > 1 && image_file[1] == ':'))
    {
      pgm_filename = image_file;
    }
    else
    {
      // 相对路径：与YAML文件同目录
      size_t last_slash = filename.find_last_of("/\\");
      if (last_slash != std::string::npos)
      {
        std::string dir = filename.substr(0, last_slash + 1);
        pgm_filename = dir + image_file;
      }
      else
      {
        // YAML文件在当前目录
        pgm_filename = image_file;
      }
    }
    
    ROS_INFO("构建的PGM文件路径: %s", pgm_filename.c_str());
    
    // 检查PGM文件是否存在
    std::ifstream test_file(pgm_filename);
    if (!test_file.good())
    {
      last_error_ = "PGM文件不存在: " + pgm_filename;
      ROS_ERROR("PGM文件不存在: %s", pgm_filename.c_str());
      
      // 尝试在几个可能的位置查找
      std::vector<std::string> search_paths = {
        image_file,  // 原始名称
        "maps/" + image_file,  // maps目录
        "../maps/" + image_file,  // 上级maps目录
        "src/ros_map_edit/maps/" + image_file  // 完整相对路径
      };
      
      for (const auto& search_path : search_paths)
      {
        std::ifstream search_file(search_path);
        if (search_file.good())
        {
          search_file.close();
          pgm_filename = search_path;
          ROS_INFO("在替代路径找到PGM文件: %s", pgm_filename.c_str());
          break;
        }
      }
    }
    else
    {
      test_file.close();
    }
    
    // 加载PGM文件，使用YAML文件中的参数
    ROS_INFO("尝试加载PGM文件: %s", pgm_filename.c_str());
    bool success = loadPGMWithParams(pgm_filename, map, occupied_thresh, free_thresh, negate);
    
    if (success)
    {
      ROS_INFO("PGM文件加载成功: %dx%d像素", map.info.width, map.info.height);
    }
    else
    {
      ROS_ERROR("PGM文件加载失败: %s", last_error_.c_str());
    }
    
    return success;
  }
  catch (const std::exception& e)
  {
    last_error_ = "Error parsing YAML: " + std::string(e.what());
    ROS_ERROR("YAML解析错误: %s", e.what());
    return false;
  }
}

bool MapFileManager::saveYAML(const std::string& filename, const nav_msgs::OccupancyGrid& map)
{
  try
  {
    std::ofstream file(filename);
    if (!file.is_open())
    {
      last_error_ = "Failed to create YAML file: " + filename;
      return false;
    }

    // Generate PGM filename
    std::string base = filename.substr(0, filename.find_last_of("."));
    std::string pgm_filename = base + ".pgm";
    std::string pgm_basename = pgm_filename.substr(pgm_filename.find_last_of("/\\") + 1);
    
    // Save PGM file
    if (!savePGM(pgm_filename, map))
    {
      return false;
    }
    
    // Write YAML
    file << "image: " << pgm_basename << "\n";
    file << "resolution: " << map.info.resolution << "\n";
    file << "origin: [" << map.info.origin.position.x << ", " 
         << map.info.origin.position.y << ", 0.0]\n";
    file << "negate: 0\n";
    file << "occupied_thresh: 0.65\n";
    file << "free_thresh: 0.196\n";
    
    return true;
  }
  catch (const std::exception& e)
  {
    last_error_ = "Error writing YAML: " + std::string(e.what());
    return false;
  }
}

} // end namespace ros_map_edit 