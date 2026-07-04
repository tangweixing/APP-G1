#ifndef MAP_FILE_MANAGER_H
#define MAP_FILE_MANAGER_H

#include <string>
#include <vector>
#include <jsoncpp/json/json.h>
#include <nav_msgs/OccupancyGrid.h>
#include <geometry_msgs/Point.h>
#include "virtual_wall_tool.h"
#include "region_tool.h"

namespace ros_map_edit
{

class MapFileManager
{
public:
  MapFileManager();
  virtual ~MapFileManager();

  // Virtual walls I/O
  bool loadVirtualWalls(const std::string& filename, std::vector<VirtualWall>& walls);
  bool saveVirtualWalls(const std::string& filename, const std::vector<VirtualWall>& walls);

  // Regions I/O
  bool loadRegions(const std::string& filename, std::vector<Region>& regions);
  bool saveRegions(const std::string& filename, const std::vector<Region>& regions);

  // Map I/O
  bool loadMap(const std::string& filename, nav_msgs::OccupancyGrid& map);
  bool saveMap(const std::string& filename, const nav_msgs::OccupancyGrid& map);
  bool saveMapImage(const std::string& filename, const nav_msgs::OccupancyGrid& map);

  // 一键保存所有文件
  bool saveMapFiles(const std::string& yaml_filename);
  bool saveMapFiles(const std::string& yaml_filename, const nav_msgs::OccupancyGrid& map);
  bool saveVirtualWallsFile(const std::string& filename);
  bool saveVirtualWallsFile(const std::string& filename, const std::vector<VirtualWall>& walls);
  bool saveRegionsFile(const std::string& filename);
  bool saveRegionsFile(const std::string& filename, const std::vector<Region>& regions);

  // Utility functions
  std::string getLastError() const { return last_error_; }
  
private:
  // JSON helpers
  Json::Value pointToJson(const geometry_msgs::Point& point);
  geometry_msgs::Point jsonToPoint(const Json::Value& json);
  
  // Map file format helpers
  bool loadPGM(const std::string& filename, nav_msgs::OccupancyGrid& map);
  bool loadPGMWithParams(const std::string& filename, nav_msgs::OccupancyGrid& map,
                         double occupied_thresh, double free_thresh, bool negate);
  bool savePGM(const std::string& filename, const nav_msgs::OccupancyGrid& map);
  bool loadYAML(const std::string& filename, nav_msgs::OccupancyGrid& map);
  bool saveYAML(const std::string& filename, const nav_msgs::OccupancyGrid& map);

  std::string last_error_;
};

} // end namespace ros_map_edit

#endif // MAP_FILE_MANAGER_H 