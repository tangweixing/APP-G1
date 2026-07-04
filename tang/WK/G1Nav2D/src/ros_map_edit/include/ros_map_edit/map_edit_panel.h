#ifndef MAP_EDIT_PANEL_H
#define MAP_EDIT_PANEL_H

#include <rviz/panel.h>
#include <QPushButton>
#include <QLineEdit>
#include <QLabel>
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QGridLayout>
#include <QFileDialog>
#include <QComboBox>
#include <QGroupBox>
#include <QMessageBox>
#include <ros/ros.h>
#include <nav_msgs/OccupancyGrid.h>
#include <nav_msgs/MapMetaData.h>

namespace ros_map_edit
{

class MapFileManager;

class MapEditPanel : public rviz::Panel
{
Q_OBJECT
public:
  MapEditPanel(QWidget* parent = 0);
  virtual ~MapEditPanel();

  virtual void onInitialize();

private Q_SLOTS:
  void saveAllFiles();
  void openMap();

private:
  void setupUI();
  void loadAndPublishMap(const std::string& filename);
  void publishMap(const nav_msgs::OccupancyGrid& map);
  void loadCorrespondingFiles(const std::string& map_file_path);
  void clearAllMessages();
  std::string getCurrentMapFile();

  // UI Components
  QVBoxLayout* main_layout_;
  
  // 一键保存组
  QGroupBox* save_group_;
  QPushButton* save_all_btn_;
  QPushButton* open_map_btn_;
  QLabel* current_map_label_;
  
  // 状态显示
  QLabel* status_label_;
  QLabel* info_label_;
  
  // Map file manager
  MapFileManager* file_manager_;
  
  // 当前地图文件路径
  QString current_map_file_;
};

} // end namespace ros_map_edit

#endif // MAP_EDIT_PANEL_H 