#include <map>
#include <mutex>
#include <vector>
#include <thread>
#include <csignal>
#include <ros/ros.h>

#include <gtsam/geometry/Rot3.h>
#include <gtsam/geometry/Pose3.h>
#include <gtsam/nonlinear/ISAM2.h>
#include <gtsam/nonlinear/Values.h>
#include <gtsam/slam/PriorFactor.h>
#include <gtsam/slam/BetweenFactor.h>
#include <gtsam/nonlinear/NonlinearFactorGraph.h>

#include <pcl/io/pcd_io.h>
#include <pcl/registration/icp.h>
#include <pcl/filters/voxel_grid.h>
#include <pcl/kdtree/kdtree_flann.h>

#include <nav_msgs/Path.h>
#include <nav_msgs/Odometry.h>
#include <geometry_msgs/PoseStamped.h>
#include <tf2_ros/transform_broadcaster.h>
#include <visualization_msgs/Marker.h>
#include <visualization_msgs/MarkerArray.h>

#include "lio_builder/lio_builder.h"
#include "fastlio/SaveMap.h"
#include "localizer/icp_localizer.h"

#include <tf/transform_datatypes.h>
#include <Eigen/Dense>
#include <string>
#include <sstream>
#include <pcl/filters/statistical_outlier_removal.h>

bool terminate_flag = false;

// 读取参数并构造变换矩阵
Eigen::Matrix4f getLidar2BaseFromParam(const ros::NodeHandle& nh) {
    std::vector<double> xyz, rpy;
    nh.param<std::vector<double>>("/lidar2base_xyz", xyz, {0,0,0});
    nh.param<std::vector<double>>("/lidar2base_rpy", rpy, {0,0.45,0});
    if(xyz.size()!=3 || rpy.size()!=3) {
        ROS_WARN("lidar2base param size error, use identity.");
        return Eigen::Matrix4f::Identity();
    }
    ROS_WARN("lidar2base_xyz: [%f, %f, %f]", xyz[0], xyz[1], xyz[2]);
    ROS_WARN("lidar2base_rpy: [%f, %f, %f]", rpy[0], rpy[1], rpy[2]);
    tf::Matrix3x3 rot;
    rot.setRPY(rpy[0], rpy[1], rpy[2]);
    tf::Vector3 trans(xyz[0], xyz[1], xyz[2]);
    tf::Transform tf_pose(rot, trans);

    Eigen::Matrix4f mat = Eigen::Matrix4f::Identity();
    for(int i=0;i<3;++i) {
        for(int j=0;j<3;++j)
            mat(i,j) = tf_pose.getBasis()[i][j];
        mat(i,3) = tf_pose.getOrigin()[i];
    }
    return mat;
}

class ZaxisPriorFactor : public gtsam::NoiseModelFactor1<gtsam::Pose3>
{
    double z_;

public:
    ZaxisPriorFactor(gtsam::Key key, const gtsam::SharedNoiseModel &noise, double z)
        : gtsam::NoiseModelFactor1<gtsam::Pose3>(noise, key), z_(z)
    {
    }
    virtual ~ZaxisPriorFactor()
    {
    }
    virtual gtsam::Vector evaluateError(const gtsam::Pose3 &p, boost::optional<gtsam::Matrix &> H = boost::none) const
    {
        auto z = p.translation()(2);
        if (H)
        {
            gtsam::Matrix Jac = gtsam::Matrix::Zero(1, 6);
            Jac << 0.0, 0.0, 0.0, 0.0, 0.0, 1.0;
            (*H) = Jac;
        }
        return gtsam::Vector1(z - z_);
    }
};



struct LoopPair
{
    LoopPair(int p, int c, float s, Eigen::Matrix3d &dr, Eigen::Vector3d &dp) : pre_idx(p), cur_idx(c), score(s), diff_rot(dr), diff_pos(dp) {}
    int pre_idx;
    int cur_idx;
    Eigen::Matrix3d diff_rot;
    Eigen::Vector3d diff_pos;
    double score;
};

struct Pose6D
{
    Pose6D(int i, double t, Eigen::Matrix3d lr, Eigen::Vector3d lp) : index(i), time(t), local_rot(lr), local_pos(lp) {}
    void setGlobalPose(const Eigen::Matrix3d &gr, const Eigen::Vector3d &gp)
    {
        global_rot = gr;
        global_pos = gp;
    }
    void addOffset(const Eigen::Matrix3d &offset_rot, const Eigen::Vector3d &offset_pos)
    {
        global_rot = offset_rot * local_rot;
        global_pos = offset_rot * local_pos + offset_pos;
    }

    void getOffset(Eigen::Matrix3d &offset_rot, Eigen::Vector3d &offset_pos)
    {
        offset_rot = global_rot * local_rot.transpose();
        offset_pos = -global_rot * local_rot.transpose() * local_pos + global_pos;
    }
    int index;
    double time;
    Eigen::Matrix3d local_rot;
    Eigen::Vector3d local_pos;
    Eigen::Matrix3d global_rot;
    Eigen::Vector3d global_pos;
    // Eigen::Vector3d gravity;
};

struct SharedData
{
    bool key_pose_added = false;
    std::mutex mutex;
    Eigen::Matrix3d offset_rot = Eigen::Matrix3d::Identity();
    Eigen::Vector3d offset_pos = Eigen::Vector3d::Zero();
    std::vector<Pose6D> key_poses;
    std::vector<Pose6D> cache_unfiltered_key_poses; // 新增
    std::vector<LoopPair> loop_pairs;
    std::vector<std::pair<int, int>> loop_history;
    std::vector<fastlio::PointCloudXYZI::Ptr> cloud_history;
    std::vector<fastlio::PointCloudXYZI::Ptr> ground_cloud_history; // 新增
    std::vector<fastlio::PointCloudXYZI::Ptr> cache_unfiltered_cloud_history; // 新增
};

struct LoopParams
{
    double rad_thresh = 0.4;
    double dist_thresh = 2.5;
    double unfilter_rad_thresh = 0.02;
    double unfilter_dist_thresh = 0.1;
    double time_thresh = 30.0;
    double loop_pose_search_radius = 10.0;
    int loop_pose_index_thresh = 5;
    double submap_resolution = 0.2;
    int submap_search_num = 20;
    double loop_icp_thresh = 0.3;
    bool activate = true;
};

class LoopClosureThread
{
public:
    void init()
    {
        // 1. 初始化 GTSAM 增量图优化器 ISAM2，并设置相关参数
        gtsam::ISAM2Params isam2_params;
        isam2_params.relinearizeThreshold = 0.01;  // 重新线性化阈值（误差大于此值时重新线性化）
        isam2_params.relinearizeSkip = 1;          // 每次都检查是否需要重新线性化
        isam2_ = std::make_shared<gtsam::ISAM2>(isam2_params);  // 创建 ISAM2 优化器实例

        // 2. 初始化历史关键帧的 KdTree 和点云容器（用于空间搜索）
        kdtree_history_poses_.reset(new pcl::KdTreeFLANN<pcl::PointXYZ>);
        cloud_history_poses_.reset(new pcl::PointCloud<pcl::PointXYZ>);

        // 3. 初始化回环子图的下采样滤波器
        sub_map_downsize_filter_.reset(new pcl::VoxelGrid<fastlio::PointType>);
        sub_map_downsize_filter_->setLeafSize(
            loop_params_.submap_resolution,
            loop_params_.submap_resolution,
            loop_params_.submap_resolution
        );

        // 4. 初始化 ICP 匹配器（用于回环配准）
        icp_.reset(new pcl::IterativeClosestPoint<fastlio::PointType, fastlio::PointType>);
        icp_->setMaxCorrespondenceDistance(50);     // 最大对应点距离（单位：米）
        icp_->setMaximumIterations(50);               // 最大迭代次数
        icp_->setTransformationEpsilon(1e-6);       // 收敛判据：变换差异小于该值
        icp_->setEuclideanFitnessEpsilon(1e-6);       // 收敛判据：整体均方误差变化小于该值
        icp_->setRANSACIterations(0);                 // 不使用 RANSAC（提高速度）
    }

    void setShared(std::shared_ptr<SharedData> share_data)
    {
        shared_data_ = share_data;
    }
    void setRate(const double &rate)
    {
        rate_ = std::make_shared<ros::Rate>(rate);
    }
    void setRate(std::shared_ptr<ros::Rate> rate)
    {
        rate_ = rate;
    }
    LoopParams &mutableParams()
    {
        return loop_params_;
    }

    fastlio::PointCloudXYZI::Ptr getSubMaps(std::vector<Pose6D> &pose_list, //搜索当前index的前后search_num的关键帧
                                            std::vector<fastlio::PointCloudXYZI::Ptr> &cloud_list,
                                            int index,
                                            int search_num)
    {
        // 创建一个空点云，用于存储拼接后的子地图
        fastlio::PointCloudXYZI::Ptr cloud(new fastlio::PointCloudXYZI);

        // 确定拼接的关键帧索引范围 [min_index, max_index]
        int max_size = pose_list.size();
        int min_index = std::max(0, index - search_num);
        int max_index = std::min(max_size - 1, index + search_num);

        // 遍历这些关键帧
        for (int i = min_index; i <= max_index; i++)
        {
            Pose6D &p = pose_list[i];

            // 构建该帧的位姿变换矩阵 T（从局部 -> 全局）
            Eigen::Matrix4d T = Eigen::Matrix4d::Identity();
            T.block<3, 3>(0, 0) = p.global_rot;  // 旋转
            T.block<3, 1>(0, 3) = p.global_pos;  // 平移

            // 对当前关键帧的点云进行位姿变换（变换到全局坐标系下）
            fastlio::PointCloudXYZI::Ptr temp_cloud(new fastlio::PointCloudXYZI);
            pcl::transformPointCloud(*cloud_list[p.index], *temp_cloud, T);

            // 将当前帧变换后的点云添加到总子图中
            *cloud += *temp_cloud;
        }

        // 对拼接后的点云执行体素滤波下采样
        sub_map_downsize_filter_->setInputCloud(cloud);
        sub_map_downsize_filter_->filter(*cloud);

        return cloud;  // 返回下采样后的局部地图子图（全局坐标系）
    }

    /**
     * @brief 回环检测主线程入口（重载 operator()），循环进行回环检测与后端优化
     * 
     * 每次循环执行以下逻辑：
     * 1. 等待时间周期
     * 2. 条件检查（是否启用、关键帧数量是否足够等）
     * 3. 从共享数据中复制最新关键帧
     * 4. 检测回环（loopCheck）
     * 5. 构建因子图（addOdomFactor + addLoopFactor）
     * 6. 优化图并更新位姿（smoothAndUpdate）
     */
    void operator()()
    {
        while (ros::ok())
        {
            // ⏳ 1. 控制频率，避免过于频繁地执行回环检测
            rate_->sleep();

            // ❌ 2. 判断是否中止线程
            if (terminate_flag)
                break;

            // ❌ 3. 未启用回环检测，跳过
            if (!loop_params_.activate)
                continue;

            // ❌ 4. 关键帧数量不足，跳过
            if (shared_data_->key_poses.size() < loop_params_.loop_pose_index_thresh)
                continue;

            // ❌ 5. 没有新关键帧添加，跳过
            if (!shared_data_->key_pose_added)
                continue;

            // ✅ 6. 新关键帧可用，置为 false，准备处理
            shared_data_->key_pose_added = false;

            // 🔐 7. 拷贝共享数据中的 key poses，避免数据竞争
            {
                std::lock_guard<std::mutex> lock(shared_data_->mutex);
                lastest_index_ = shared_data_->key_poses.size() - 1;
                temp_poses_.clear();
                temp_poses_.assign(shared_data_->key_poses.begin(), shared_data_->key_poses.end());
            }

            // 🔄 8. 回环检测（基于 KdTree + ICP）
            loopCheck();

            // ➕ 9. 向因子图中添加里程计因子
            addOdomFactor();

            // 🔗 10. 添加检测到的回环约束
            addLoopFactor();

            // 🧠 11. 通过 ISAM2 优化图并更新关键帧全局位姿
            smoothAndUpdate();
        }

    }

private:
    std::shared_ptr<SharedData> shared_data_;

    std::shared_ptr<ros::Rate> rate_;

    LoopParams loop_params_;

    std::vector<Pose6D> temp_poses_;

    int previous_index_ = 0;

    int lastest_index_;

    bool loop_found_ = false;

    gtsam::Values initialized_estimate_;

    gtsam::Values optimized_estimate_;

    std::shared_ptr<gtsam::ISAM2> isam2_;

    gtsam::NonlinearFactorGraph gtsam_graph_;

    pcl::KdTreeFLANN<pcl::PointXYZ>::Ptr kdtree_history_poses_;

    pcl::PointCloud<pcl::PointXYZ>::Ptr cloud_history_poses_;

    pcl::VoxelGrid<fastlio::PointType>::Ptr sub_map_downsize_filter_;

    pcl::IterativeClosestPointWithNormals<fastlio::PointType, fastlio::PointType>::Ptr icp_;


    /**
     * @brief 回环检测主函数（每次关键帧添加后调用）
     * 
     * 实现流程：
     * 1. 从历史关键帧构建 KD-Tree；
     * 2. 基于当前帧位置查找附近的历史帧；
     * 3. 筛选满足时间约束的候选帧；
     * 4. 构建子地图并使用 ICP 匹配；
     * 5. 若匹配成功，记录回环约束（位姿变换 + 匹配得分）。
     */
    void loopCheck()
    {
        // 🚫 若当前关键帧为空，直接返回
        if (temp_poses_.empty())
            return;
        int cur_index = temp_poses_.size() - 1;
        int pre_index = -1;


        // 📦 构造历史关键帧的点云（只包含位置）
        cloud_history_poses_->clear();
        for (Pose6D &p : temp_poses_)
        {
            pcl::PointXYZ point;
            point.x = p.global_pos(0);
            point.y = p.global_pos(1);
            point.z = p.global_pos(2);
            cloud_history_poses_->push_back(point);
        }
        // 🧱 构建 Kd-Tree
        kdtree_history_poses_->setInputCloud(cloud_history_poses_);

        // 🔎 半径搜索：找到当前帧附近的历史帧索引
        std::vector<int> ids;
        std::vector<float> sqdists;
        kdtree_history_poses_->radiusSearch(cloud_history_poses_->back(),
                                            loop_params_.loop_pose_search_radius,
                                            ids, sqdists, 0);

        // ⏱️ 筛选时间差满足条件的历史帧，作为回环候选帧
        for (int i = 0; i < ids.size(); i++)
        {
            int id = ids[i];
            if (std::abs(temp_poses_[id].time - temp_poses_.back().time) > loop_params_.time_thresh)
            {
                pre_index = id;
                break;
            }
        }

        // ❌ 检查是否满足最低条件（非当前帧 & 回环距离大于阈值）
        if (pre_index == -1 || pre_index == cur_index ||
            cur_index - pre_index < loop_params_.loop_pose_index_thresh)
            return;


        // 📍 获取当前帧点云和历史子地图
        fastlio::PointCloudXYZI::Ptr cur_cloud = getSubMaps(temp_poses_, shared_data_->cloud_history, cur_index, 0);
        fastlio::PointCloudXYZI::Ptr sub_maps = getSubMaps(temp_poses_, shared_data_->cloud_history, pre_index, loop_params_.submap_search_num);

        // 转为 pcl::PointXYZI 以用于 ICP 配准
        pcl::PointCloud<pcl::PointXYZI>::Ptr cur_cloud_xyz(new pcl::PointCloud<pcl::PointXYZI>);
        pcl::PointCloud<pcl::PointXYZI>::Ptr sub_maps_xyz(new pcl::PointCloud<pcl::PointXYZI>);
        pcl::copyPointCloud(*cur_cloud, *cur_cloud_xyz);
        pcl::copyPointCloud(*sub_maps, *sub_maps_xyz);

        // 添加法向量，用于点面 ICP
        cur_cloud = fastlio::IcpLocalizer::addNorm(cur_cloud_xyz);
        sub_maps = fastlio::IcpLocalizer::addNorm(sub_maps_xyz);


        // ⚙️ ICP 匹配当前帧与历史子地图
        icp_->setInputSource(cur_cloud);
        icp_->setInputTarget(sub_maps);
        
        fastlio::PointCloudXYZI::Ptr aligned(new fastlio::PointCloudXYZI);

        icp_->align(*aligned, Eigen::Matrix4f::Identity());

        float score = icp_->getFitnessScore();

        // ❌ ICP未收敛或匹配质量不佳，放弃回环
        if (!icp_->hasConverged() || score > loop_params_.loop_icp_thresh)
            return;


        // ✅ 匹配成功，记录回环信息
        ROS_INFO("Detected LOOP: %d %d %f", pre_index, cur_index, score);
        shared_data_->loop_history.emplace_back(pre_index, cur_index);
        loop_found_ = true;

        // ⛓️ 计算 pre -> cur 的位姿变换
        Eigen::Matrix4d T_pre_cur = icp_->getFinalTransformation().cast<double>();
        Eigen::Matrix3d R12 = temp_poses_[pre_index].global_rot.transpose()
                            * T_pre_cur.block<3, 3>(0, 0)
                            * temp_poses_[cur_index].global_rot;
        Eigen::Vector3d t12 = temp_poses_[pre_index].global_rot.transpose()
                            * (T_pre_cur.block<3, 3>(0, 0) * temp_poses_[cur_index].global_pos
                            + T_pre_cur.block<3, 1>(0, 3)
                            - temp_poses_[pre_index].global_pos);

        // 📥 存储回环约束（供图优化使用）
        shared_data_->loop_pairs.emplace_back(pre_index, cur_index, score, R12, t12);

    }

    /**
     * @brief 添加里程计约束（Odometry Factor）到 GTSAM 图优化中。
     * 
     * - 对每一对连续关键帧，构造相对位姿（BetweenFactor）；
     * - 对第一个帧添加先验因子（PriorFactor）；
     * - 将节点加入到初始估计中。
     * 
     * 注：该函数仅处理从 previous_index_ 到 lastest_index_ 的新关键帧。
     */

    void addOdomFactor()
    {
        // 遍历新加入的关键帧对 [previous_index_, lastest_index_)
        for (int i = previous_index_; i < lastest_index_; i++)
        {
            // p1 是第 i 个关键帧，p2 是第 i+1 个关键帧
            Pose6D &p1 = temp_poses_[i];
            Pose6D &p2 = temp_poses_[i + 1];


            // 第一个节点加入先验因子
            if (i == 0)
            {
                // 将第一个节点插入初始估计
                initialized_estimate_.insert(i, gtsam::Pose3(
                    gtsam::Rot3(p1.local_rot),
                    gtsam::Point3(p1.local_pos)
                ));

                // 构造一个很小协方差的先验因子（几乎固定初始节点）
                gtsam::noiseModel::Diagonal::shared_ptr noise = gtsam::noiseModel::Diagonal::Variances(gtsam::Vector6::Ones() * 1e-12);

                gtsam_graph_.add(gtsam::PriorFactor<gtsam::Pose3>(
                    i,
                    gtsam::Pose3(gtsam::Rot3(p1.local_rot), gtsam::Point3(p1.local_pos)),
                    noise
                ));
            }

            // 插入 p2 的初始估计值
            initialized_estimate_.insert(i + 1, gtsam::Pose3(
                gtsam::Rot3(p2.local_rot),
                gtsam::Point3(p2.local_pos)
            ));

            // 计算 p1 到 p2 的相对变换（以 p1 为坐标系）
            Eigen::Matrix3d R12 = p1.local_rot.transpose() * p2.local_rot;
            Eigen::Vector3d t12 = p1.local_rot.transpose() * (p2.local_pos - p1.local_pos);

            // // 📌 可选 Z 轴 prior，常用于飞行器或漂移限制
            // auto noise_prior = gtsam::noiseModel::Diagonal::Variances(gtsam::Vector1::Ones());
            // gtsam_graph_.add(ZaxisPriorFactor(i + 1, noise_prior, p2.local_pos(2)));


            // 构造 Between 因子（两个帧之间的相对变换因子）
            gtsam::noiseModel::Diagonal::shared_ptr noise = gtsam::noiseModel::Diagonal::Variances((gtsam::Vector(6) << 1e-6, 1e-6, 1e-6, 1e-4, 1e-4, 1e-6).finished());

            gtsam_graph_.add(gtsam::BetweenFactor<gtsam::Pose3>(
                i, i + 1,
                gtsam::Pose3(gtsam::Rot3(R12), gtsam::Point3(t12)),
                noise
            ));
        }
        // ⚙️ 更新 previous_index_，避免重复添加因子
        previous_index_ = lastest_index_;

    }

    /**
     * @brief 向 GTSAM 因子图中添加闭环检测产生的约束（Loop Closure Factor）。
     *
     * - 检查是否发现了闭环；
     * - 遍历闭环对，将其作为 BetweenFactor 加入因子图；
     * - 每个闭环因子的协方差取决于 ICP 匹配分数（score）；
     * - 添加完毕后清空缓存列表。
     */
    void addLoopFactor()
    {
        // 没有发现闭环则直接返回
        if (!loop_found_)
            return;

        // 没有闭环对（LoopPair）也直接返回
        if (shared_data_->loop_pairs.empty())
            return;
        // 遍历所有闭环对，添加约束因子
        for (LoopPair &lp : shared_data_->loop_pairs)
        {
            // 构造 pre_idx -> cur_idx 的相对位姿
            gtsam::Pose3 pose_between(
                gtsam::Rot3(lp.diff_rot),         // 相对旋转
                gtsam::Point3(lp.diff_pos)        // 相对平移
            );

            // 构造 BetweenFactor，权重由 score 决定
            gtsam_graph_.add(gtsam::BetweenFactor<gtsam::Pose3>(
                lp.pre_idx,
                lp.cur_idx,
                pose_between,
                gtsam::noiseModel::Diagonal::Variances(
                    gtsam::Vector6::Ones() * lp.score   // 使用 ICP score 缩放协方差
                )
            ));
        }
        // 清空闭环对缓存，避免重复添加
        shared_data_->loop_pairs.clear();
    }

    /**
     * @brief 执行闭环图优化，并将优化后的结果回写到关键帧轨迹中。
     *
     * 主要功能：
     * 1. 调用 ISAM2 增量优化器，更新图；
     * 2. 获取最新位姿估计，并更新临时/共享关键帧列表；
     * 3. 根据最后一帧优化结果更新坐标系偏移；
     * 4. 用优化后的结果修正历史关键帧和后续关键帧的全局位姿。
     */

    void smoothAndUpdate()
    {
        // ===【1】更新ISAM2图优化器：加入当前因子图和初始估计值 ===
        isam2_->update(gtsam_graph_, initialized_estimate_);
        isam2_->update();  // 触发优化
        // ===【2】闭环优化加强：多次迭代提高闭环传播效果 ===
        if (loop_found_)
        {
            isam2_->update();
            isam2_->update();
            isam2_->update();
            isam2_->update();
            isam2_->update();
            loop_found_ = false;
        }
        // ===【3】清空图结构，准备下次增量添加 ===
        gtsam_graph_.resize(0);
        initialized_estimate_.clear();

        // ===【4】提取最新优化结果中的当前帧的位姿 ===
        optimized_estimate_ = isam2_->calculateBestEstimate();
        gtsam::Pose3 latest_estimate = optimized_estimate_.at<gtsam::Pose3>(lastest_index_);
        temp_poses_[lastest_index_].global_rot = latest_estimate.rotation().matrix().cast<double>();
        temp_poses_[lastest_index_].global_pos = latest_estimate.translation().matrix().cast<double>();

        // ===【5】根据当前帧优化结果计算全局坐标偏移量 ===
        Eigen::Matrix3d offset_rot;
        Eigen::Vector3d offset_pos;
        temp_poses_[lastest_index_].getOffset(offset_rot, offset_pos);

        // ===【6】保存坐标偏移到共享数据中（线程安全）===
        shared_data_->mutex.lock();
        int current_size = shared_data_->key_poses.size();
        shared_data_->offset_rot = offset_rot;
        shared_data_->offset_pos = offset_pos;
        shared_data_->mutex.unlock();

        // ===【7】用优化结果更新历史关键帧的全局位姿 ===
        for (int i = 0; i < lastest_index_; i++)
        {
            gtsam::Pose3 temp_pose = optimized_estimate_.at<gtsam::Pose3>(i);
            shared_data_->key_poses[i].global_rot = temp_pose.rotation().matrix().cast<double>();
            shared_data_->key_poses[i].global_pos = temp_pose.translation().matrix().cast<double>();
        }

        // ===【8】对闭环后未参与优化的关键帧进行偏移更新 ===
        for (int i = lastest_index_; i < current_size; i++)
        {
            shared_data_->key_poses[i].addOffset(offset_rot, offset_pos);
        }
    }
};

class MapBuilderROS
{
public:
    ros::Publisher* getGroundCloudPub() {
        return &ground_cloud_pub_;
    }
    MapBuilderROS(tf2_ros::TransformBroadcaster &br, std::shared_ptr<SharedData> share_data) : br_(br)
    {
        shared_data_ = share_data;
        initPatams();           //初始化坐标系以及建图回环参数
        initSubscribers();      //初始化订阅者
        initPublishers();       //初始化发布者
        initServices();         //初始化保存地图服务

        lio_builder_ = std::make_shared<fastlio::LIOBuilder>(lio_params_);
        loop_closure_.setRate(loop_rate_);
        loop_closure_.setShared(share_data);
        loop_closure_.init();
        loop_thread_ = std::make_shared<std::thread>(std::ref(loop_closure_));
    }
    void initPatams()
    {
        nh_.param<std::string>("map_frame", global_frame_, "map");
        nh_.param<std::string>("local_frame", local_frame_, "local");
        nh_.param<std::string>("body_frame", body_frame_, "body");
        nh_.param<std::string>("imu_topic", imu_data_.topic, "/livox/imu");
        nh_.param<std::string>("livox_topic", livox_data_.topic, "/livox/lidar");
        double local_rate, loop_rate;
        nh_.param<double>("local_rate", local_rate, 20.0);
        nh_.param<double>("loop_rate", loop_rate, 1.0);
        local_rate_ = std::make_shared<ros::Rate>(local_rate);
        loop_rate_ = std::make_shared<ros::Rate>(loop_rate);
        nh_.param<double>("lio_builder/det_range", lio_params_.det_range, 100.0);
        nh_.param<double>("lio_builder/cube_len", lio_params_.cube_len, 500.0);
        nh_.param<double>("lio_builder/resolution", lio_params_.resolution, 0.1);
        nh_.param<double>("lio_builder/move_thresh", lio_params_.move_thresh, 1.5);
        nh_.param<bool>("lio_builder/align_gravity", lio_params_.align_gravity, true);
        nh_.param<std::vector<double>>("lio_builder/imu_ext_rot", lio_params_.imu_ext_rot, std::vector<double>());
        nh_.param<std::vector<double>>("lio_builder/imu_ext_pos", lio_params_.imu_ext_pos, std::vector<double>());

        nh_.param<bool>("loop_closure/activate", loop_closure_.mutableParams().activate, true);
        nh_.param<double>("loop_closure/rad_thresh", loop_closure_.mutableParams().rad_thresh, 0.4);
        nh_.param<double>("loop_closure/dist_thresh", loop_closure_.mutableParams().dist_thresh, 2.5);
        nh_.param<double>("loop_closure/unfilter_rad_thresh", loop_closure_.mutableParams().unfilter_rad_thresh, 0.1);
        nh_.param<double>("loop_closure/unfilter_dist_thresh", loop_closure_.mutableParams().unfilter_dist_thresh, 0.5);
        nh_.param<double>("loop_closure/time_thresh", loop_closure_.mutableParams().time_thresh, 30.0);
        nh_.param<double>("loop_closure/loop_pose_search_radius", loop_closure_.mutableParams().loop_pose_search_radius, 10.0);
        nh_.param<int>("loop_closure/loop_pose_index_thresh", loop_closure_.mutableParams().loop_pose_index_thresh, 5);
        nh_.param<double>("loop_closure/submap_resolution", loop_closure_.mutableParams().submap_resolution, 0.2);
        nh_.param<int>("loop_closure/submap_search_num", loop_closure_.mutableParams().submap_search_num, 20);
        nh_.param<double>("loop_closure/loop_icp_thresh", loop_closure_.mutableParams().loop_icp_thresh, 0.3);
    }

    void initSubscribers()
    {
        imu_sub_ = nh_.subscribe(imu_data_.topic, 1000, &ImuData::callback, &imu_data_);
        livox_sub_ = nh_.subscribe(livox_data_.topic, 1000, &LivoxData::callback, &livox_data_);
    }

    void initPublishers()
    {
        merged_cloud_pub_ = nh_.advertise<sensor_msgs::PointCloud2>("merged_cache_cloud", 1, true);
        local_cloud_pub_ = nh_.advertise<sensor_msgs::PointCloud2>("local_cloud", 1000);
        body_cloud_pub_ = nh_.advertise<sensor_msgs::PointCloud2>("body_cloud", 1000);
        body_cloud_org_pub_ = nh_.advertise<sensor_msgs::PointCloud2>("velodyne_points", 1000);
        odom_pub_ = nh_.advertise<nav_msgs::Odometry>("slam_odom", 1000);
        loop_mark_pub_ = nh_.advertise<visualization_msgs::MarkerArray>("loop_mark", 1000);

        local_path_pub_ = nh_.advertise<nav_msgs::Path>("local_path", 1000);
        global_path_pub_ = nh_.advertise<nav_msgs::Path>("global_path", 1000);
        ground_cloud_pub_ = nh_.advertise<sensor_msgs::PointCloud2>("ground_cloud", 1, true);
    }

    void initServices()
    {
        save_map_server_ = nh_.advertiseService("save_map", &MapBuilderROS::saveMapCallback, this);
    }

    void publishCloud(ros::Publisher &publisher, const sensor_msgs::PointCloud2 &cloud_to_pub)
    {
        if (publisher.getNumSubscribers() == 0)
            return;
        publisher.publish(cloud_to_pub);
    }

    void publishOdom(const nav_msgs::Odometry &odom_to_pub)
    {
        if (odom_pub_.getNumSubscribers() == 0)
            return;
        odom_pub_.publish(odom_to_pub);
    }

    void publishLocalPath()
    {
        if (local_path_pub_.getNumSubscribers() == 0)
            return;

        if (shared_data_->key_poses.empty())
            return;

        nav_msgs::Path path;
        path.header.frame_id = global_frame_;
        path.header.stamp = ros::Time().fromSec(current_time_);
        for (Pose6D &p : shared_data_->key_poses)
        {
            geometry_msgs::PoseStamped pose;
            pose.header.frame_id = global_frame_;
            pose.header.stamp = ros::Time().fromSec(current_time_);
            pose.pose.position.x = p.local_pos(0);
            pose.pose.position.y = p.local_pos(1);
            pose.pose.position.z = p.local_pos(2);
            Eigen::Quaterniond q(p.local_rot);
            pose.pose.orientation.x = q.x();
            pose.pose.orientation.y = q.y();
            pose.pose.orientation.z = q.z();
            pose.pose.orientation.w = q.w();
            path.poses.push_back(pose);
        }
        local_path_pub_.publish(path);
    }

    void publishGlobalPath()
    {
        if (global_path_pub_.getNumSubscribers() == 0)
            return;

        if (shared_data_->key_poses.empty())
            return;
        nav_msgs::Path path;
        path.header.frame_id = global_frame_;
        path.header.stamp = ros::Time().fromSec(current_time_);
        for (Pose6D &p : shared_data_->key_poses)
        {
            geometry_msgs::PoseStamped pose;
            pose.header.frame_id = global_frame_;
            pose.header.stamp = ros::Time().fromSec(current_time_);
            pose.pose.position.x = p.global_pos(0);
            pose.pose.position.y = p.global_pos(1);
            pose.pose.position.z = p.global_pos(2);
            Eigen::Quaterniond q(p.global_rot);
            pose.pose.orientation.x = q.x();
            pose.pose.orientation.y = q.y();
            pose.pose.orientation.z = q.z();
            pose.pose.orientation.w = q.w();
            path.poses.push_back(pose);
        }
        global_path_pub_.publish(path);
    }

    void publishLoopMark()
    {
        if (loop_mark_pub_.getNumSubscribers() == 0)
            return;
        if (shared_data_->loop_history.empty())
            return;
        visualization_msgs::MarkerArray marker_array;
        visualization_msgs::Marker nodes_marker;

        nodes_marker.header.frame_id = global_frame_;
        nodes_marker.header.stamp = ros::Time().fromSec(current_time_);
        nodes_marker.ns = "loop_nodes";
        nodes_marker.id = 0;
        nodes_marker.type = visualization_msgs::Marker::SPHERE_LIST;
        nodes_marker.action = visualization_msgs::Marker::ADD;
        nodes_marker.pose.orientation.w = 1.0;
        nodes_marker.scale.x = 0.3;
        nodes_marker.scale.y = 0.3;
        nodes_marker.scale.z = 0.3;
        nodes_marker.color.r = 1.0;
        nodes_marker.color.g = 0.8;
        nodes_marker.color.b = 0.0;
        nodes_marker.color.a = 1.0;

        visualization_msgs::Marker edges_marker;
        edges_marker.header.frame_id = global_frame_;
        edges_marker.header.stamp = ros::Time().fromSec(current_time_);
        edges_marker.ns = "loop_edges";
        edges_marker.id = 1;
        edges_marker.type = visualization_msgs::Marker::LINE_LIST;
        edges_marker.action = visualization_msgs::Marker::ADD;
        edges_marker.pose.orientation.w = 1.0;
        edges_marker.scale.x = 0.1;

        edges_marker.color.r = 0.0;
        edges_marker.color.g = 0.8;
        edges_marker.color.b = 0.0;
        edges_marker.color.a = 1.0;
        for (auto &p : shared_data_->loop_history)
        {
            Pose6D &p1 = shared_data_->key_poses[p.first];
            Pose6D &p2 = shared_data_->key_poses[p.second];
            geometry_msgs::Point point1;
            point1.x = p1.global_pos(0);
            point1.y = p1.global_pos(1);
            point1.z = p1.global_pos(2);
            geometry_msgs::Point point2;
            point2.x = p2.global_pos(0);
            point2.y = p2.global_pos(1);
            point2.z = p2.global_pos(2);
            nodes_marker.points.push_back(point1);
            nodes_marker.points.push_back(point2);
            edges_marker.points.push_back(point1);
            edges_marker.points.push_back(point2);
        }
        marker_array.markers.push_back(nodes_marker);
        marker_array.markers.push_back(edges_marker);
        loop_mark_pub_.publish(marker_array);
    }

    bool saveMapCallback(fastlio::SaveMap::Request &req, fastlio::SaveMap::Response &res)
    {
        std::string file_path = req.save_path;
        fastlio::PointCloudXYZI::Ptr cloud(new fastlio::PointCloudXYZI);
        for (Pose6D &p : shared_data_->key_poses)
        {
            fastlio::PointCloudXYZI::Ptr temp_cloud(new fastlio::PointCloudXYZI);
            // Eigen::Quaterniond grav_diff = Eigen::Quaterniond::FromTwoVectors(p.gravity, Eigen::Vector3d(0, 0, -1));
            pcl::transformPointCloud(*shared_data_->cloud_history[p.index],
                                     *temp_cloud,
                                     p.global_pos.cast<float>(),
                                     Eigen::Quaternionf(p.global_rot.cast<float>()));
            *cloud += *temp_cloud;
        }
        if (cloud->empty())
        {
            res.status = false;
            res.message = "Empty cloud!";
            return false;
        }
        res.status = true;
        res.message = "Save map success!";
        writer_.writeBinaryCompressed(file_path, *cloud);

        // 额外保存地面点云地图（用 req.resolution 作为标志位：>= 1.0 时启用）
        if (req.resolution >= 1.0f && shared_data_->ground_cloud_history.size() > 0)
        {
            // 推导 ground_map 路径：xxx.pcd → xxx_ground.pcd
            std::string ground_path = file_path;
            size_t dot_pos = ground_path.find_last_of('.');
            if (dot_pos != std::string::npos)
            {
                ground_path = ground_path.substr(0, dot_pos) + "_ground.pcd";
            }
            else
            {
                ground_path = ground_path + "_ground.pcd";
            }

            ROS_INFO("[saveMap] Saving ground map to: %s", ground_path.c_str());
            bool ground_ok = saveGroundMap(ground_path, shared_data_);
            if (ground_ok)
            {
                res.message = "Save map success! (with ground map)";
                ROS_INFO("[saveMap] Ground map saved successfully");
            }
            else
            {
                ROS_WARN("[saveMap] Ground map save failed (continuing anyway)");
            }
        }

        return true;
    }

    bool saveGroundMap(const std::string& file_path, std::shared_ptr<SharedData> shared_data) {
        fastlio::PointCloudXYZI::Ptr ground_map(new fastlio::PointCloudXYZI);
        shared_data->mutex.lock();
        for (const auto& p : shared_data->key_poses) {
            int idx = p.index;
            if (idx < shared_data->ground_cloud_history.size() && shared_data->ground_cloud_history[idx]) {
                // 变换到全局坐标
                fastlio::PointCloudXYZI::Ptr temp(new fastlio::PointCloudXYZI);
                pcl::transformPointCloud(*shared_data->ground_cloud_history[idx], *temp, p.global_pos.cast<float>(), Eigen::Quaternionf(p.global_rot.cast<float>()));
                *ground_map += *temp;
            }
        }
        shared_data->mutex.unlock();
        if (ground_map->empty()) return false;
        pcl::PCDWriter writer;
        writer.writeBinaryCompressed(file_path, *ground_map);
        return true;
    }


    /**
     * @brief 判断当前状态是否满足关键帧添加条件，并在满足时添加关键帧。
     * 
     * 当系统刚开始或当前帧与上一个关键帧的位姿变换超过设定的平移或旋转阈值时，
     * 将当前帧添加为新的关键帧，同时记录其去畸变后的点云和位姿信息。
     */
    bool addKeyPose()
    {
        int idx = shared_data_->key_poses.size();
        int unfiltered_idx = shared_data_->cache_unfiltered_key_poses.size();
        // === 1. 初始关键帧：如果为空，则直接添加第一帧 === //
        if (shared_data_->cache_unfiltered_key_poses.empty())
        {
            std::lock_guard<std::mutex> lock(shared_data_->mutex);  // 加锁保护共享资源
            shared_data_->cache_unfiltered_key_poses.emplace_back(
                unfiltered_idx,
                current_time_,
                current_state_.rot.toRotationMatrix(),
                current_state_.pos
            );
            shared_data_->cache_unfiltered_cloud_history.push_back(lio_builder_->cloudUndistortedBody());
        }

        if (shared_data_->key_poses.empty())
        {
            std::lock_guard<std::mutex> lock(shared_data_->mutex);  // 加锁保护共享资源
            shared_data_->key_poses.emplace_back(
                idx,
                current_time_,
                current_state_.rot.toRotationMatrix(),
                current_state_.pos
            );
            shared_data_->key_poses.back().addOffset(shared_data_->offset_rot, shared_data_->offset_pos);
            shared_data_->key_pose_added = true;

            shared_data_->cloud_history.push_back(lio_builder_->cloudUndistortedBody());
            shared_data_->ground_cloud_history.push_back(shared_data_->cache_unfiltered_cloud_history.back());
            shared_data_->cache_unfiltered_cloud_history.clear();
            shared_data_->cache_unfiltered_key_poses.clear();
            return true;  
        }

        // === 2. 非首帧：判断是否满足添加关键帧的条件 === //
        Pose6D &last_key_pose = shared_data_->key_poses.back();
        Pose6D &last_unfiltered_key_pose = shared_data_->cache_unfiltered_key_poses.back();
        // 位姿差计算（相对于上一关键帧）
        Eigen::Matrix3d diff_rot = last_key_pose.local_rot.transpose() * current_state_.rot.toRotationMatrix();
        Eigen::Vector3d diff_pose = last_key_pose.local_rot.transpose() * (current_state_.pos - last_key_pose.local_pos);
        Eigen::Vector3d rpy = rotate2rpy(diff_rot);  // 将旋转差转换为 roll-pitch-yaw 表示

        Eigen::Matrix3d unfiltered_diff_rot = last_unfiltered_key_pose.local_rot.transpose() * current_state_.rot.toRotationMatrix();
        Eigen::Vector3d unfiltered_diff_pose = last_unfiltered_key_pose.local_rot.transpose() * (current_state_.pos - last_unfiltered_key_pose.local_pos);
        Eigen::Vector3d unfiltered_rpy = rotate2rpy(unfiltered_diff_rot);  // 将旋转差转换为 roll-pitch-yaw 表示
        //=== 3. 判断是否超过设定的关键帧添加阈值 === //
        if (unfiltered_diff_pose.norm() > loop_closure_.mutableParams().unfilter_dist_thresh ||
            std::abs(unfiltered_rpy(0)) > loop_closure_.mutableParams().unfilter_rad_thresh ||
            std::abs(unfiltered_rpy(1)) > loop_closure_.mutableParams().unfilter_rad_thresh ||
            std::abs(unfiltered_rpy(2)) > loop_closure_.mutableParams().unfilter_rad_thresh)
        {
            std::lock_guard<std::mutex> lock(shared_data_->mutex);  // 加锁
            shared_data_->cache_unfiltered_key_poses.emplace_back(
                unfiltered_idx,
                current_time_,
                current_state_.rot.toRotationMatrix(),
                current_state_.pos
            );
            shared_data_->cache_unfiltered_cloud_history.push_back(lio_builder_->cloudUndistortedBody());
        }

        if (diff_pose.norm() > loop_closure_.mutableParams().dist_thresh ||
            std::abs(rpy(0)) > loop_closure_.mutableParams().rad_thresh ||
            std::abs(rpy(1)) > loop_closure_.mutableParams().rad_thresh ||
            std::abs(rpy(2)) > loop_closure_.mutableParams().rad_thresh)
        {
            std::lock_guard<std::mutex> lock(shared_data_->mutex);  // 加锁
            shared_data_->key_poses.emplace_back(
                idx,
                current_time_,
                current_state_.rot.toRotationMatrix(),
                current_state_.pos
            );
            shared_data_->key_poses.back().addOffset(shared_data_->offset_rot, shared_data_->offset_pos);
            shared_data_->key_pose_added = true;

            shared_data_->cloud_history.push_back(lio_builder_->cloudUndistortedBody());

            // === 新增：处理缓存 ===
            if (!shared_data_->cache_unfiltered_cloud_history.empty()) {
                // 存储到 ground_cloud_history
                if (shared_data_->ground_cloud_history.size() <= idx)
                    shared_data_->ground_cloud_history.resize(idx + 1);

                    pcl::PointCloud<pcl::PointXYZINormal>::Ptr merged(new pcl::PointCloud<pcl::PointXYZINormal>);
                    pcl::PointCloud<pcl::PointXYZINormal>::Ptr cloud(new pcl::PointCloud<pcl::PointXYZINormal>);
                    for (Pose6D &p : shared_data_->cache_unfiltered_key_poses)
                    {
                        pcl::PointCloud<pcl::PointXYZINormal>::Ptr temp_cloud(new pcl::PointCloud<pcl::PointXYZINormal>);
                        pcl::transformPointCloud(*shared_data_->cache_unfiltered_cloud_history[p.index],
                                                *temp_cloud,
                                                p.local_pos.cast<float>(),
                                                Eigen::Quaternionf(p.local_rot.cast<float>()));
                        *cloud += *temp_cloud;
                    }
                    // // 可视化 merged
                    // sensor_msgs::PointCloud2 merged_msg;
                    // pcl::toROSMsg(*cloud, merged_msg);
                    // merged_msg.header.frame_id = "local"; // 或你需要的 frame
                    // merged_msg.header.stamp = ros::Time::now();
                    // merged_cloud_pub_.publish(merged_msg);

                    // 构造世界坐标系到 LiDAR 的反变换
                    Eigen::Affine3f T_lidar_to_world = Eigen::Affine3f::Identity();
                    T_lidar_to_world.linear() = current_state_.rot.toRotationMatrix().cast<float>();
                    T_lidar_to_world.translation() = Eigen::Vector3f(
                        current_state_.pos(0),
                        current_state_.pos(1),
                        current_state_.pos(2)
                    );

                    Eigen::Affine3f T_world_to_lidar = T_lidar_to_world.inverse();  // 🔁 取逆

                    pcl::transformPointCloud(*cloud, *merged, T_world_to_lidar);
                shared_data_->ground_cloud_history[idx] = merged;
                shared_data_->cache_unfiltered_cloud_history.clear();
                shared_data_->cache_unfiltered_key_poses.clear();
            }
            return true;  
        }
        return false;  
    }


    /**
     * @brief 主运行函数，用于持续执行 LIO 系统的建图流程。
     * 
     * 此函数包含一个主循环，每次迭代进行如下操作：
     * 
     * 1. 维持 ROS 节点运行，处理回调（ros::spinOnce）与频率控制（sleep）。
     * 2. 检查终止标志 terminate_flag，支持平稳退出。
     * 3. 从同步模块 measure_group_ 获取同步后的 IMU 与雷达数据（syncPackage）。
     *    - 若未成功同步，则跳过本轮。
     * 4. 将同步数据传入 lio_builder_ 进行建图与状态估计。
     *    - 若系统仍处于初始化阶段（Status::INITIALIZE），则跳过本轮。
     * 5. 获取当前估计状态 current_state_ 和时间戳 current_time_。
     * 6. 发布坐标变换：
     *    - global_frame → local_frame（用 offset 位姿）
     *    - local_frame → body_frame（用当前 LIO 状态）
     * 7. 发布里程计信息（Odometry）和关键帧（KeyPose）。
     * 8. 发布点云：
     *    - body 坐标系下去畸变后的点云（cloudUndistortedBody）
     *    - 世界坐标系下的点云（cloudWorld）
     * 9. 发布路径、闭环等可视化标记。
     * 
     * 循环退出时，等待子线程 loop_thread_ 结束，并输出终止信息。
     */
    void run()
    {
        while (ros::ok())
        {
            local_rate_->sleep();
            ros::spinOnce();
            if (terminate_flag)
                break;
            if (!measure_group_.syncPackage(imu_data_, livox_data_))        //同步IMU和雷达数据
                continue;
            lio_builder_->mapping(measure_group_);
            if (lio_builder_->currentStatus() == fastlio::Status::INITIALIZE)
                continue;
            current_time_ = measure_group_.lidar_time_end;
            current_state_ = lio_builder_->currentState();
            br_.sendTransform(eigen2Transform(shared_data_->offset_rot,
                                              shared_data_->offset_pos,
                                              global_frame_,
                                              local_frame_,
                                              current_time_));
            br_.sendTransform(eigen2Transform(current_state_.rot.toRotationMatrix(),
                                              current_state_.pos,
                                              local_frame_,
                                              body_frame_,
                                              current_time_));

            publishOdom(eigen2Odometry(current_state_.rot.toRotationMatrix(),
                                       current_state_.pos,
                                       local_frame_,
                                       body_frame_,
                                       current_time_));
            //计算addKeyPose的时间
            // auto start = std::chrono::steady_clock::now();
            if(addKeyPose()) {}//添加关键帧
            // auto end = std::chrono::steady_clock::now();
            // std::chrono::duration<double> elapsed_seconds = end - start;
            // std::cout << "Add KeyPose Time: " << elapsed_seconds.count() << " seconds" << std::endl;
            // publishCloud(body_cloud_org_pub_,
             //                pcl2msg(measure_group_.lidar_org,
              //                       body_frame_,
             //                        current_time_));

            publishCloud(body_cloud_pub_,
                         pcl2msg(lio_builder_->cloudUndistortedBody(),
                                 body_frame_,
                                 current_time_));
            publishCloud(local_cloud_pub_,
                         pcl2msg(lio_builder_->cloudWorld(),
                                 local_frame_,
                                 current_time_));
            publishLocalPath();
            publishGlobalPath();
            publishLoopMark();
        }

        loop_thread_->join();
        std::cout << "MAPPING NODE IS DOWN!" << std::endl;
    }

private:
    ros::NodeHandle nh_;
    std::string global_frame_;
    std::string local_frame_;
    std::string body_frame_;
    double current_time_;
    // kf::State current_state_;
    fastlio::state_ikfom current_state_;
    ImuData imu_data_;
    LivoxData livox_data_;
    MeasureGroup measure_group_;
    fastlio::LioParams lio_params_;
    std::shared_ptr<fastlio::LIOBuilder> lio_builder_;
    std::shared_ptr<SharedData> shared_data_;
    std::shared_ptr<ros::Rate> local_rate_;
    std::shared_ptr<ros::Rate> loop_rate_;
    LoopClosureThread loop_closure_;
    std::shared_ptr<std::thread> loop_thread_;

    tf2_ros::TransformBroadcaster &br_;

    ros::Subscriber imu_sub_;

    ros::Subscriber livox_sub_;

    ros::Publisher body_cloud_pub_,merged_cloud_pub_;

    ros::Publisher body_cloud_org_pub_;

    ros::Publisher local_cloud_pub_;

    ros::Publisher odom_pub_;

    ros::Publisher loop_mark_pub_;

    ros::Publisher local_path_pub_;

    ros::Publisher global_path_pub_;

    ros::Publisher ground_cloud_pub_;

    ros::ServiceServer save_map_server_;

    pcl::PCDWriter writer_;
};

class GroundExtractionThread {
public:
    void setShared(std::shared_ptr<SharedData> shared_data) {
        shared_data_ = shared_data;
    }
    void setLidar2Base(const Eigen::Matrix4f& tf) { lidar2base_ = tf; }
    void operator()() {
        size_t last_processed = 0;
        while (ros::ok()) {
            // 检查是否有新关键帧
            shared_data_->mutex.lock();
            size_t cur_size = shared_data_->cloud_history.size();
            shared_data_->mutex.unlock();
            if (last_processed < cur_size) {
                for (; last_processed < cur_size; ++last_processed) {
                    extractGround(last_processed);
                }
            }
            std::this_thread::sleep_for(std::chrono::milliseconds(100));
        }
    }
    // 简单高度阈值法地面提取
    void extractGround(size_t idx) {
        shared_data_->mutex.lock();
        auto cloud = shared_data_->ground_cloud_history[idx];
        shared_data_->mutex.unlock();

        // 1. 先将点云变换到 base_link 坐标系
        pcl::PointCloud<fastlio::PointType>::Ptr cloud_base(new pcl::PointCloud<fastlio::PointType>);
        pcl::transformPointCloud(*cloud, *cloud_base, lidar2base_);

        // 2. 以 base_link 的z为准做地面提取
        pcl::PointCloud<fastlio::PointType>::Ptr ground_base(new pcl::PointCloud<fastlio::PointType>);
        for (const auto& pt : cloud_base->points) {
            if (pt.z < ground_z_thresh_ && pt.x > 0 && pt.x < 5 && pt.y > -5 && pt.y < 5 && pt.z > -1) ground_base->points.push_back(pt);
        }

        // 3. 再将地面点云从 base_link 变回雷达坐标系
        pcl::PointCloud<fastlio::PointType>::Ptr ground_lidar(new pcl::PointCloud<fastlio::PointType>);
        Eigen::Matrix4f base2lidar = lidar2base_.inverse();
        pcl::transformPointCloud(*ground_base, *ground_lidar, base2lidar);

        // 4. 存储到 ground_cloud_history
        shared_data_->mutex.lock();
        if (shared_data_->ground_cloud_history.size() <= idx)
            shared_data_->ground_cloud_history.resize(idx + 1);
        shared_data_->ground_cloud_history[idx] = ground_lidar;
        shared_data_->mutex.unlock();
    }


    void setGroundZThresh(float z) { ground_z_thresh_ = z; }
private:
    std::shared_ptr<SharedData> shared_data_;
    float ground_z_thresh_ = 0.0; // 可调参数
     Eigen::Matrix4f lidar2base_ = Eigen::Matrix4f::Identity();
};

class GroundCloudPublishThread {
public:
    void setShared(std::shared_ptr<SharedData> shared_data) {
        shared_data_ = shared_data;
    }
    void setPublisher(ros::Publisher* pub) {
        pub_ = pub;
    }
    void setFrame(const std::string& frame) {
        frame_id_ = frame;
    }
    void setRate(double hz) {
        rate_ = hz;
    }
    // 保存地面地图到PCD文件
    bool saveGroundMap(const std::string& file_path) {
        fastlio::PointCloudXYZI::Ptr ground_map(new fastlio::PointCloudXYZI);
        shared_data_->mutex.lock();
        for (const auto& p : shared_data_->key_poses) {
            int idx = p.index;
            if (idx < shared_data_->ground_cloud_history.size() && shared_data_->ground_cloud_history[idx]) {
                fastlio::PointCloudXYZI::Ptr temp(new fastlio::PointCloudXYZI);
                pcl::transformPointCloud(*shared_data_->ground_cloud_history[idx], *temp, p.global_pos.cast<float>(), Eigen::Quaternionf(p.global_rot.cast<float>()));
                *ground_map += *temp;
            }
        }
        shared_data_->mutex.unlock();
        if (ground_map->empty()) return false;
        pcl::PCDWriter writer;
        writer.writeBinaryCompressed(file_path, *ground_map);
        return true;
    }

    bool saveMap(const std::string& file_path) {
        fastlio::PointCloudXYZI::Ptr map(new fastlio::PointCloudXYZI);
        shared_data_->mutex.lock();
        for (const auto& p : shared_data_->key_poses) {
            int idx = p.index;
            if (idx < shared_data_->cloud_history.size() && shared_data_->cloud_history[idx]) {
                fastlio::PointCloudXYZI::Ptr temp(new fastlio::PointCloudXYZI);
                pcl::transformPointCloud(*shared_data_->cloud_history[idx], *temp, p.global_pos.cast<float>(), Eigen::Quaternionf(p.global_rot.cast<float>()));
                *map += *temp;
            }
        }
        shared_data_->mutex.unlock();
        if (map->empty()) return false;
        pcl::PCDWriter writer;
        writer.writeBinaryCompressed(file_path, *map);
        return true;
    }

    // 保存关键帧位姿到文本文件
    bool saveKeyPoses(const std::string& file_path) {
        shared_data_->mutex.lock();
        std::ofstream ofs(file_path);
        if (!ofs.is_open()) {
            shared_data_->mutex.unlock();
            return false;
        }
        for (const auto& p : shared_data_->key_poses) {
            ofs << p.index << " " << p.global_pos.transpose() << " ";
            Eigen::Quaterniond q(p.global_rot);
            ofs << q.x() << " " << q.y() << " " << q.z() << " " << q.w() << std::endl;
        }
        ofs.close();
        shared_data_->mutex.unlock();
        return true;
    }
    void operator()() {
        ros::Rate r(rate_);
        while (ros::ok()) {
            fastlio::PointCloudXYZI::Ptr ground_map(new fastlio::PointCloudXYZI);
            shared_data_->mutex.lock();
            for (const auto& p : shared_data_->key_poses) {
                int idx = p.index;
                if (idx < shared_data_->ground_cloud_history.size() && shared_data_->ground_cloud_history[idx]) {
                    fastlio::PointCloudXYZI::Ptr temp(new fastlio::PointCloudXYZI);
                    pcl::transformPointCloud(*shared_data_->ground_cloud_history[idx], *temp, p.global_pos.cast<float>(), Eigen::Quaternionf(p.global_rot.cast<float>()));
                    *ground_map += *temp;
                }
            }
            shared_data_->mutex.unlock();
            if (!ground_map->empty() && pub_ && pub_->getNumSubscribers() > 0) {
                sensor_msgs::PointCloud2 msg;
                pcl::toROSMsg(*ground_map, msg);
                msg.header.frame_id = frame_id_;
                msg.header.stamp = ros::Time::now();
                pub_->publish(msg);
            }
            r.sleep();
        }
    }
private:
    std::shared_ptr<SharedData> shared_data_;
    ros::Publisher* pub_ = nullptr;
    std::string frame_id_ = "map";
    double rate_ = 1.0;
};

GroundCloudPublishThread* g_ground_pub_thread = nullptr;
std::string g_map_path = "/tmp/map.pcd"; // 默认保存路径
std::string g_ground_map_path = "/tmp/ground_map.pcd";
std::string g_keyposes_path = "/tmp/key_poses.txt";


void signalHandler(int signum)
{
    std::cout << "SHUTTING DOWN MAPPING NODE!" << std::endl;
    terminate_flag = true;
    if (g_ground_pub_thread) {
        std::cout << "Auto-saving ground map and key poses..." << std::endl;
        g_ground_pub_thread->saveMap(g_map_path);
        g_ground_pub_thread->saveGroundMap(g_ground_map_path);
        g_ground_pub_thread->saveKeyPoses(g_keyposes_path);
        std::cout << "Map saved to: " << g_map_path << std::endl;
        std::cout << "Ground map saved to: " << g_ground_map_path << std::endl;
        std::cout << "Key poses saved to: " << g_keyposes_path << std::endl;
    }
}

int main(int argc, char **argv)
{
    ros::init(argc, argv, "map_builder_node");
    ros::NodeHandle nh("/");
    tf2_ros::TransformBroadcaster br;
    signal(SIGINT, signalHandler);
    //创建一个 SharedData 的共享智能指针对象 share_data，并在整个系统中作为共享资源传递
    //让多个模块或线程安全地访问和修改同一份数据
    std::shared_ptr<SharedData> share_data = std::make_shared<SharedData>();

    // 启动地面提取线程
    GroundExtractionThread ground_thread;
    Eigen::Matrix4f lidar2base = getLidar2BaseFromParam(nh);
    ground_thread.setLidar2Base(lidar2base);
    ground_thread.setShared(share_data);
    std::thread ground_extract_worker(std::ref(ground_thread));

    MapBuilderROS map_builder(br, share_data);

    // 启动地面点云发布线程
    GroundCloudPublishThread ground_pub_thread;
    ground_pub_thread.setShared(share_data);
    ground_pub_thread.setPublisher(map_builder.getGroundCloudPub());
    ground_pub_thread.setFrame("map"); // 或根据你的frame设置
    ground_pub_thread.setRate(1.0);    // 1Hz，可根据需要调整
    std::thread ground_pub_worker(std::ref(ground_pub_thread));

    // 设置全局指针和保存路径
    g_ground_pub_thread = &ground_pub_thread;
    g_map_path = "/home/unitree/tang/WK/G1Nav2D/src/fastlio2/PCD/map.pcd";
    g_ground_map_path = "/home/unitree/tang/WK/G1Nav2D/src/fastlio2/PCD/ground_map.pcd";
    g_keyposes_path = "/home/unitree/tang/WK/G1Nav2D/src/fastlio2/path/key_poses.txt";
    map_builder.run();
    ground_pub_worker.join();
    return 0;
}
