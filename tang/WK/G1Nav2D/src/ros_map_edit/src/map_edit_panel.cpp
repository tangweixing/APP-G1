#include "ros_map_edit/map_edit_panel.h"
#include "ros_map_edit/map_file_manager.h"
#include "ros_map_edit/tool_manager.h"
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QGridLayout>
#include <QGroupBox>
#include <QPushButton>
#include <QLineEdit>
#include <QLabel>
#include <QFileDialog>
#include <QMessageBox>
#include <QDir>
#include <visualization_msgs/MarkerArray.h>

namespace ros_map_edit
{

MapEditPanel::MapEditPanel(QWidget* parent)
  : rviz::Panel(parent)
  , main_layout_(nullptr)
  , file_manager_(nullptr)
{
  setupUI();
  file_manager_ = new MapFileManager();
}

MapEditPanel::~MapEditPanel()
{
  delete file_manager_;
}

void MapEditPanel::onInitialize()
{
  status_label_->setText("就绪 - 请先打开一个地图文件");
}

void MapEditPanel::setupUI()
{
  main_layout_ = new QVBoxLayout;
  
  // 一键保存组
  save_group_ = new QGroupBox("文件管理");
  QVBoxLayout* save_layout = new QVBoxLayout;
  
  // 当前地图显示
  current_map_label_ = new QLabel("当前地图: 未加载");
  current_map_label_->setStyleSheet("QLabel { color: #333; font-weight: bold; padding: 5px; }");
  save_layout->addWidget(current_map_label_);
  
  // 一键保存按钮
  save_all_btn_ = new QPushButton("一键保存所有文件");
  save_all_btn_->setStyleSheet("QPushButton { background-color: #4CAF50; color: white; font-size: 14px; padding: 8px; }");
  save_layout->addWidget(save_all_btn_);
  
  // 打开地图按钮
  open_map_btn_ = new QPushButton("打开地图");
  save_layout->addWidget(open_map_btn_);
  
  save_group_->setLayout(save_layout);
  
  // 状态显示
  status_label_ = new QLabel("就绪 - 请先打开一个地图文件");
  status_label_->setStyleSheet("QLabel { background-color: #f0f0f0; padding: 8px; border: 1px solid #ccc; border-radius: 4px; }");
  
  // 文件说明
  info_label_ = new QLabel(
    "保存文件说明:\n"
    "• map.yaml - 地图配置文件\n"
    "• map.pgm - 地图图像文件\n" 
    "• map.json - 虚拟墙数据\n"
    "• map_region.json - 区域数据\n\n"
    "提示: 文件将保存到当前地图的同一目录");
  info_label_->setStyleSheet("QLabel { color: #666; font-size: 11px; padding: 8px; }");
  
  // 组装主布局
  main_layout_->addWidget(save_group_);
  main_layout_->addWidget(new QLabel("状态:"));
  main_layout_->addWidget(status_label_);
  main_layout_->addWidget(info_label_);
  main_layout_->addStretch();
  
  setLayout(main_layout_);
  
  // 连接信号
  connect(save_all_btn_, SIGNAL(clicked()), this, SLOT(saveAllFiles()));
  connect(open_map_btn_, SIGNAL(clicked()), this, SLOT(openMap()));
}

void MapEditPanel::saveAllFiles()
{
  // 获取当前地图文件路径
  std::string current_map_file = getCurrentMapFile();
  if (current_map_file.empty())
  {
    QMessageBox::warning(this, "警告", "请先加载一个地图文件作为基准");
    return;
  }
  
  // 从当前地图文件路径提取目录和基础名称
  QFileInfo map_info(QString::fromStdString(current_map_file));
  QString base_dir = map_info.absolutePath();
  QString base_name = map_info.baseName(); // 不包含扩展名
  
  // 构建保存文件路径
  QString yaml_file = base_dir + "/" + base_name + ".yaml";
  QString pgm_file = base_dir + "/" + base_name + ".pgm";
  QString vw_file = base_dir + "/" + base_name + ".json";
  QString region_file = base_dir + "/" + base_name + "_region.json";
  
  bool success = true;
  QStringList saved_files;
  QStringList failed_files;
  
  try
  {
    // 获取工具管理器实例
    ToolManager& toolManager = ToolManager::getInstance();
    
    // 1. 保存地图 (yaml + pgm)
    MapEraserTool* eraserTool = toolManager.getMapEraserTool();
    if (eraserTool && eraserTool->getCurrentMap().data.size() > 0)
    {
      // 使用橡皮擦工具的当前地图数据
      if (file_manager_->saveMapFiles(yaml_file.toStdString(), eraserTool->getCurrentMap()))
      {
        saved_files << "地图文件 (yaml+pgm)";
      }
      else
      {
        failed_files << "地图文件: " + QString::fromStdString(file_manager_->getLastError());
        success = false;
      }
    }
    else
    {
      // 使用默认方法（从话题获取）
      if (file_manager_->saveMapFiles(yaml_file.toStdString()))
      {
        saved_files << "地图文件 (yaml+pgm)";
      }
      else
      {
        failed_files << "地图文件: " + QString::fromStdString(file_manager_->getLastError());
        success = false;
      }
    }
    
    // 2. 保存虚拟墙
    VirtualWallTool* wallTool = toolManager.getVirtualWallTool();
    if (wallTool)
    {
      std::vector<VirtualWall> walls = wallTool->getVirtualWalls();
      if (file_manager_->saveVirtualWallsFile(vw_file.toStdString(), walls))
      {
        saved_files << "虚拟墙文件 (" + QString::number(walls.size()) + " 个墙体)";
      }
      else
      {
        failed_files << "虚拟墙文件: " + QString::fromStdString(file_manager_->getLastError());
        success = false;
      }
    }
    else
    {
      // 使用默认方法
      if (file_manager_->saveVirtualWallsFile(vw_file.toStdString()))
      {
        saved_files << "虚拟墙文件";
      }
      else
      {
        failed_files << "虚拟墙文件: " + QString::fromStdString(file_manager_->getLastError());
        success = false;
      }
    }
    
    // 3. 保存区域
    RegionTool* regionTool = toolManager.getRegionTool();
    if (regionTool)
    {
      std::vector<Region> regions = regionTool->getRegions();
      if (file_manager_->saveRegionsFile(region_file.toStdString(), regions))
      {
        saved_files << "区域文件 (" + QString::number(regions.size()) + " 个区域)";
      }
      else
      {
        failed_files << "区域文件: " + QString::fromStdString(file_manager_->getLastError());
        success = false;
      }
    }
    else
    {
      // 使用默认方法
      if (file_manager_->saveRegionsFile(region_file.toStdString()))
      {
        saved_files << "区域文件";
      }
      else
      {
        failed_files << "区域文件: " + QString::fromStdString(file_manager_->getLastError());
        success = false;
      }
    }
    
    // 显示结果
    QString message = "保存到: " + base_dir + "\n\n";
    if (!saved_files.isEmpty())
    {
      message += "✓ 成功保存: " + saved_files.join(", ") + "\n";
    }
    if (!failed_files.isEmpty())
    {
      message += "✗ 保存失败: " + failed_files.join(", ") + "\n";
    }
    
    if (success)
    {
      status_label_->setText("所有文件已保存: " + base_name);
      QMessageBox::information(this, "保存成功", message);
    }
    else
    {
      status_label_->setText("部分文件保存失败");
      QMessageBox::warning(this, "保存部分失败", message);
    }
  }
  catch (const std::exception& e)
  {
    QString error_msg = "保存过程中出现错误: " + QString::fromStdString(e.what());
    status_label_->setText("保存失败");
    QMessageBox::critical(this, "保存错误", error_msg);
  }
}

std::string MapEditPanel::getCurrentMapFile()
{
  // 首先检查用户是否手动加载了地图文件
  if (!current_map_file_.isEmpty())
  {
    return current_map_file_.toStdString();
  }
  
  // 从参数服务器获取当前地图文件路径
  ros::NodeHandle nh;
  std::string map_file;
  if (nh.getParam("/map_server/map_file", map_file))
  {
    return map_file;
  }
  
  return "";
}

void MapEditPanel::openMap()
{
  // 设置默认路径为ros_map_edit/maps目录
  QString default_path = "src/ros_map_edit/maps";
  
  // 如果目录不存在，尝试其他可能的路径
  QDir maps_dir(default_path);
  if (!maps_dir.exists()) {
    // 尝试相对于工作目录的路径
    QStringList possible_paths = {
      "ros_map_edit/maps",
      "../src/ros_map_edit/maps", 
      "../../src/ros_map_edit/maps",
      QDir::homePath() + "/ros_ws/cursor_ws/src/ros_map_edit/maps"
    };
    
    for (const QString& path : possible_paths) {
      if (QDir(path).exists()) {
        default_path = path;
        break;
      }
    }
  }
  
  QString filename = QFileDialog::getOpenFileName(this,
                                                  "打开地图文件",
                                                  default_path,
                                                  "YAML files (*.yaml);;PGM files (*.pgm);;All files (*.*)");
  
  if (!filename.isEmpty())
  {
    current_map_file_ = filename;
    
    // 先清空所有消息，再加载并发布新地图
    clearAllMessages();
    loadAndPublishMap(filename.toStdString());
    
    // 更新当前地图显示
    QString display_name = QFileInfo(filename).fileName();
    current_map_label_->setText("当前地图: " + display_name);
    current_map_label_->setStyleSheet("QLabel { color: #007700; font-weight: bold; padding: 5px; }");
  }
}

void MapEditPanel::loadAndPublishMap(const std::string& filename)
{
  try
  {
    nav_msgs::OccupancyGrid map;
    
    ROS_INFO("开始加载地图文件: %s", filename.c_str());
    status_label_->setText("正在加载地图: " + QString::fromStdString(filename));
    
    // 根据文件扩展名决定加载方式
    std::string ext = filename.substr(filename.find_last_of(".") + 1);
    ROS_INFO("检测到文件扩展名: %s", ext.c_str());
    
    if (ext == "yaml" || ext == "yml")
    {
      // 加载YAML配置的地图
      ROS_INFO("尝试加载YAML格式地图...");
      if (file_manager_->loadMap(filename, map))
      {
        ROS_INFO("地图加载成功: %dx%d像素, 分辨率: %.3f m/pixel", 
                 map.info.width, map.info.height, map.info.resolution);
        publishMap(map);
        
        // 地图加载成功后，清空并重新加载对应的虚拟墙和区域
        loadCorrespondingFiles(filename);
        
        status_label_->setText("地图已加载: " + QFileInfo(QString::fromStdString(filename)).fileName());
      }
      else
      {
        QString error = QString::fromStdString(file_manager_->getLastError());
        ROS_ERROR("地图加载失败: %s", error.toStdString().c_str());
        status_label_->setText("加载失败: " + error);
      }
    }
    else if (ext == "pgm")
    {
      // 直接加载PGM文件
      ROS_INFO("尝试加载PGM格式地图...");
      if (file_manager_->loadMap(filename, map))
      {
        ROS_INFO("地图加载成功: %dx%d像素, 分辨率: %.3f m/pixel", 
                 map.info.width, map.info.height, map.info.resolution);
        publishMap(map);
        
        // 地图加载成功后，清空并重新加载对应的虚拟墙和区域
        loadCorrespondingFiles(filename);
        
        status_label_->setText("地图已加载: " + QFileInfo(QString::fromStdString(filename)).fileName());
      }
      else
      {
        QString error = QString::fromStdString(file_manager_->getLastError());
        ROS_ERROR("地图加载失败: %s", error.toStdString().c_str());
        status_label_->setText("加载失败: " + error);
      }
    }
    else
    {
      QString error = "不支持的文件格式: " + QString::fromStdString(ext);
      ROS_ERROR("%s", error.toStdString().c_str());
      status_label_->setText(error);
    }
  }
  catch (const std::exception& e)
  {
    QString error = "加载出错: " + QString::fromStdString(e.what());
    ROS_ERROR("%s", error.toStdString().c_str());
    status_label_->setText(error);
  }
}

void MapEditPanel::publishMap(const nav_msgs::OccupancyGrid& map)
{
  // 创建地图发布器 - 使用静态发布器确保持续发布
  static ros::Publisher map_pub;
  static bool initialized = false;
  
  if (!initialized)
  {
    ros::NodeHandle nh;
    // 使用latched=true确保新订阅者能立即收到地图数据
    map_pub = nh.advertise<nav_msgs::OccupancyGrid>("map", 1, true);
    initialized = true;
    
    // 等待发布器准备就绪
    ros::Duration(0.5).sleep();
  }
  
  // 设置地图头信息
  nav_msgs::OccupancyGrid map_msg = map;
  map_msg.header.stamp = ros::Time::now();
  map_msg.header.frame_id = "map";
  
  // 发布地图多次以确保被接收
  for (int i = 0; i < 3; ++i)
  {
    map_pub.publish(map_msg);
    ros::Duration(0.1).sleep();
    ros::spinOnce();
  }
  
  // 输出调试信息
  QString debug_info = QString("地图已发布: %1x%2像素, 分辨率: %3m/pixel")
                      .arg(map_msg.info.width)
                      .arg(map_msg.info.height)
                      .arg(map_msg.info.resolution);
  
  status_label_->setText(debug_info);
  
  // 同时发布到map_metadata话题
  static ros::Publisher metadata_pub;
  static bool metadata_initialized = false;
  
  if (!metadata_initialized)
  {
    ros::NodeHandle nh;
    metadata_pub = nh.advertise<nav_msgs::MapMetaData>("map_metadata", 1, true);
    metadata_initialized = true;
  }
  
  metadata_pub.publish(map_msg.info);
  
  ROS_INFO("地图已发布: %dx%d, 分辨率: %.3f", 
           map_msg.info.width, map_msg.info.height, map_msg.info.resolution);
}

void MapEditPanel::loadCorrespondingFiles(const std::string& map_file_path)
{
  // 清空并重新加载对应的虚拟墙和区域文件
  try
  {
    // 获取工具管理器实例
    ToolManager& toolManager = ToolManager::getInstance();
    
    // 清空并重新加载虚拟墙
    VirtualWallTool* wallTool = toolManager.getVirtualWallTool();
    if (wallTool)
    {
      ROS_INFO("清空并重新加载虚拟墙文件...");
      wallTool->loadVirtualWallsForMap(map_file_path);
    }
    
    // 清空并重新加载区域
    RegionTool* regionTool = toolManager.getRegionTool();
    if (regionTool)
    {
      ROS_INFO("清空并重新加载区域文件...");
      regionTool->loadRegionsForMap(map_file_path);
    }
    
    ROS_INFO("已清空并重新加载地图对应的虚拟墙和区域文件");
  }
  catch (const std::exception& e)
  {
    ROS_ERROR("加载对应文件时出错: %s", e.what());
  }
}

void MapEditPanel::clearAllMessages()
{
  // 清空所有ROS话题消息，确保加载新地图时不会显示旧数据
  try
  {
    ROS_INFO("正在清空所有消息...");
    status_label_->setText("正在清空现有数据...");
    
    // 1. 清空地图消息 - 发布空地图
    static ros::Publisher map_pub;
    static ros::Publisher metadata_pub; 
    static ros::Publisher edited_map_pub;
    static bool publishers_initialized = false;
    
    if (!publishers_initialized)
    {
      ros::NodeHandle nh;
      map_pub = nh.advertise<nav_msgs::OccupancyGrid>("map", 1, true);
      metadata_pub = nh.advertise<nav_msgs::MapMetaData>("map_metadata", 1, true);
      edited_map_pub = nh.advertise<nav_msgs::OccupancyGrid>("map_edited", 1, true);
      publishers_initialized = true;
      
      // 等待发布器准备就绪
      ros::Duration(0.2).sleep();
    }
    
    // 创建空地图消息
    nav_msgs::OccupancyGrid empty_map;
    empty_map.header.stamp = ros::Time::now();
    empty_map.header.frame_id = "map";
    empty_map.info.width = 0;
    empty_map.info.height = 0;
    empty_map.info.resolution = 0.05;
    empty_map.info.origin.position.x = 0.0;
    empty_map.info.origin.position.y = 0.0;
    empty_map.info.origin.position.z = 0.0;
    empty_map.info.origin.orientation.w = 1.0;
    empty_map.data.clear();
    
    // 发布空地图消息
    for (int i = 0; i < 3; ++i)
    {
      map_pub.publish(empty_map);
      edited_map_pub.publish(empty_map);
      metadata_pub.publish(empty_map.info);
      ros::Duration(0.1).sleep();
      ros::spinOnce();
    }
    
    // 2. 清空虚拟墙和区域消息
    ToolManager& toolManager = ToolManager::getInstance();
    
    // 清空虚拟墙
    VirtualWallTool* wallTool = toolManager.getVirtualWallTool();
    if (wallTool)
    {
      ROS_INFO("清空虚拟墙消息...");
      wallTool->clearVirtualWalls();
    }
    
    // 清空区域
    RegionTool* regionTool = toolManager.getRegionTool();
    if (regionTool)
    {
      ROS_INFO("清空区域消息...");
      regionTool->clearRegions();
    }
    
    // 3. 额外确保marker话题清空
    static ros::Publisher wall_marker_pub;
    static ros::Publisher region_marker_pub;
    static bool marker_publishers_initialized = false;
    
    if (!marker_publishers_initialized)
    {
      ros::NodeHandle nh;
      wall_marker_pub = nh.advertise<visualization_msgs::MarkerArray>("virtual_walls_markers", 1, true);
      region_marker_pub = nh.advertise<visualization_msgs::MarkerArray>("region_markers", 1, true);
      marker_publishers_initialized = true;
      
      ros::Duration(0.1).sleep();
    }
    
    // 创建空的marker数组
    visualization_msgs::MarkerArray empty_markers;
    empty_markers.markers.clear();
    
    // 发布空marker数组
    for (int i = 0; i < 3; ++i)
    {
      wall_marker_pub.publish(empty_markers);
      region_marker_pub.publish(empty_markers);
      ros::Duration(0.1).sleep();
      ros::spinOnce();
    }
    
    ROS_INFO("所有消息已清空");
    status_label_->setText("现有数据已清空");
    
    // 短暂等待确保消息被接收
    ros::Duration(0.5).sleep();
    ros::spinOnce();
  }
  catch (const std::exception& e)
  {
    ROS_ERROR("清空消息时出错: %s", e.what());
    status_label_->setText("清空数据时出错");
  }
}

} // end namespace ros_map_edit

#include <pluginlib/class_list_macros.h>
PLUGINLIB_EXPORT_CLASS(ros_map_edit::MapEditPanel, rviz::Panel) 