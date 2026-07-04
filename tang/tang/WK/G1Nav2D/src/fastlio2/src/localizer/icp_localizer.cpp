#include "localizer/icp_localizer.h"
// #include <chrono>

namespace fastlio
{
    /**
     * @brief 初始化ICP定位器，加载点云地图并设置粗定位和精定位的目标点云
     * 
     * 该函数实现双层ICP定位策略：
     * 1. 粗定位（rough_map_）：使用粗体素滤波的地图，快速获得初始位姿估计
     * 2. 精定位（refine_map_）：使用精细体素滤波的地图，获得高精度位姿
     * 
     * @param pcd_path 点云地图文件路径（.pcd格式）
     * @param with_norm 是否输入点云已包含法向量信息
     *                  - true: 直接加载包含法向量的点云（PointXYZINormal）
     *                  - false: 加载XYZI点云，通过addNorm()计算法向量
     * 
     * @note 函数执行流程：
     *       1. 检查路径是否已加载，避免重复初始化
     *       2. 根据with_norm参数选择加载方式：
     *          - 不含法向量：加载XYZI → 体素滤波 → 计算法向量 → 精定位地图
     *          - 含法向量：直接加载为精定位地图
     *       3. 从精定位地图生成粗定位地图：复制点云 → 粗体素滤波 → 计算法向量
     *       4. 配置两个ICP算法的目标点云和最大迭代次数
     * 
     * @warning 确保pcd_path文件存在且格式正确，否则会导致读取失败
     */
    void IcpLocalizer::init(const std::string &pcd_path, bool with_norm)
    {
        // 避免重复加载相同的点云地图
        if (!pcd_path_.empty() && pcd_path_ == pcd_path)
            return;
        
        pcl::PCDReader reader;
        pcd_path_ = pcd_path;
        
        if (!with_norm)
        {
            // 输入点云不含法向量，需要加载XYZI点云并计算法向量
            pcl::PointCloud<pcl::PointXYZI>::Ptr cloud(new pcl::PointCloud<pcl::PointXYZI>);
            reader.read(pcd_path, *cloud);
            
            // 对原始点云进行精细体素滤波，用于精定位
            voxel_refine_filter_.setInputCloud(cloud);
            voxel_refine_filter_.filter(*cloud);
            refine_map_ = addNorm(cloud);  // 计算法向量并转换为PointXYZINormal
        }
        else
        {
            // 输入点云已包含法向量，直接加载为精定位地图
            refine_map_.reset(new PointCloudXYZI);
            reader.read(pcd_path, *refine_map_);
        }
        
        // 从精定位地图生成粗定位地图
        pcl::PointCloud<pcl::PointXYZI>::Ptr point_rough(new pcl::PointCloud<pcl::PointXYZI>);
        pcl::PointCloud<pcl::PointXYZI>::Ptr filterd_point_rough(new pcl::PointCloud<pcl::PointXYZI>);
        
        // 复制精定位地图的空间坐标和强度信息（不含法向量）
        pcl::copyPointCloud(*refine_map_, *point_rough);
        
        // 对复制的点云进行粗体素滤波，降低点云密度以提高粗定位速度
        voxel_rough_filter_.setInputCloud(point_rough);
        voxel_rough_filter_.filter(*filterd_point_rough);
        rough_map_ = addNorm(filterd_point_rough);  // 计算法向量并转换为PointXYZINormal
        
        // 配置粗定位ICP算法
        icp_rough_.setMaximumIterations(rough_iter_);
        icp_rough_.setInputTarget(rough_map_);
        
        // 配置精定位ICP算法
        icp_refine_.setMaximumIterations(refine_iter_);
        icp_refine_.setInputTarget(refine_map_);
        
        initialized_ = true;  // 标记初始化完成
    }

    /**
     * @brief 执行双层ICP点云配准，获得精确的位姿变换矩阵
     * 
     * 该函数实现分层配准策略：
     * 1. 粗配准：使用低分辨率点云进行快速初始对齐
     * 2. 精配准：基于粗配准结果进行高精度细化对齐
     * 
     * @param source 输入的源点云（待配准点云）
     * @param init_guess 初始位姿估计（4x4变换矩阵）
     * @return Eigen::Matrix4d 最终配准结果的变换矩阵
     *                         - 成功：返回精配准的最终变换矩阵
     *                         - 失败：返回零矩阵（Eigen::Matrix4d::Zero()）
     * 
     * @note 执行流程：
     *       1. 对源点云进行两种不同分辨率的体素滤波
     *       2. 为滤波后的点云计算法向量
     *       3. 粗配准：使用粗分辨率点云和初始估计进行ICP对齐
     *       4. 收敛性检查：验证粗配准是否收敛
     *       5. 精配准：使用细分辨率点云和粗配准结果进行ICP对齐
     *       6. 质量评估：检查精配准收敛性和适应度得分
     * 
     * @warning 配准可能失败的情况：
     *          - 粗配准未收敛
     *          - 精配准未收敛  
     *          - 最终适应度得分超过阈值（score_ > thresh_）
     */
    Eigen::Matrix4d IcpLocalizer::align(pcl::PointCloud<pcl::PointXYZI>::Ptr source, Eigen::Matrix4d init_guess)
    {
        success_ = false;  // 初始化配准状态为失败
        Eigen::Vector3d xyz = init_guess.block<3, 1>(0, 3);  // 提取初始位置（暂未使用）

        // === 第一步：源点云预处理 ===
        pcl::PointCloud<pcl::PointXYZI>::Ptr rough_source(new pcl::PointCloud<pcl::PointXYZI>);
        pcl::PointCloud<pcl::PointXYZI>::Ptr refine_source(new pcl::PointCloud<pcl::PointXYZI>);

        // 对源点云进行粗体素滤波，用于快速粗配准
        voxel_rough_filter_.setInputCloud(source);
        voxel_rough_filter_.filter(*rough_source);
        
        // 对源点云进行精细体素滤波，用于高精度精配准
        voxel_refine_filter_.setInputCloud(source);
        voxel_refine_filter_.filter(*refine_source);

        // 为滤波后的点云计算法向量，提升配准精度
        PointCloudXYZI::Ptr rough_source_norm = addNorm(rough_source);
        PointCloudXYZI::Ptr refine_source_norm = addNorm(refine_source);
        PointCloudXYZI::Ptr align_point(new PointCloudXYZI);  // 配准结果存储点云
        
        // === 第二步：粗配准阶段 ===
        icp_rough_.setInputSource(rough_source_norm);
        icp_rough_.align(*align_point, init_guess.cast<float>());

        score_ = icp_rough_.getFitnessScore();  // 获取粗配准适应度得分
        if (!icp_rough_.hasConverged())         // 检查粗配准是否收敛
            return Eigen::Matrix4d::Zero();

        // === 第三步：精配准阶段 ===
        // 使用粗配准结果作为精配准的初始估计
        icp_refine_.setInputSource(refine_source_norm);
        icp_refine_.align(*align_point, icp_rough_.getFinalTransformation());
        
        score_ = icp_refine_.getFitnessScore();  // 获取精配准适应度得分
        
        // === 第四步：结果验证 ===
        if (!icp_refine_.hasConverged())  // 检查精配准是否收敛
            return Eigen::Matrix4d::Zero();
        if (score_ > thresh_)             // 检查适应度得分是否满足要求
            return Eigen::Matrix4d::Zero();
            
        success_ = true;  // 标记配准成功
        return icp_refine_.getFinalTransformation().cast<double>();  // 返回最终变换矩阵
    }

    PointCloudXYZI::Ptr IcpLocalizer::addNorm(pcl::PointCloud<pcl::PointXYZI>::Ptr cloud)
    {
        pcl::PointCloud<pcl::Normal>::Ptr normals(new pcl::PointCloud<pcl::Normal>);
        pcl::search::KdTree<pcl::PointXYZI>::Ptr searchTree(new pcl::search::KdTree<pcl::PointXYZI>);
        searchTree->setInputCloud(cloud);

        pcl::NormalEstimation<pcl::PointXYZI, pcl::Normal> normalEstimator;
        normalEstimator.setInputCloud(cloud);
        normalEstimator.setSearchMethod(searchTree);
        normalEstimator.setKSearch(15);
        normalEstimator.compute(*normals);
        PointCloudXYZI::Ptr out(new PointCloudXYZI);
        pcl::concatenateFields(*cloud, *normals, *out);
        return out;
    }

    void IcpLocalizer::writePCDToFile(const std::string &path, bool detail)
    {
        if (!initialized_)
            return;
        pcl::PCDWriter writer;
        writer.writeBinaryCompressed(path, detail ? *refine_map_ : *rough_map_);
    }

    void IcpLocalizer::setParams(double refine_resolution, double rough_resolution, int refine_iter, int rough_iter, double thresh)
    {
        refine_resolution_ = refine_resolution;
        rough_resolution_ = rough_resolution;
        refine_iter_ = refine_iter;
        rough_iter_ = rough_iter;
        thresh_ = thresh;
    }

    void IcpLocalizer::setSearchParams(double xy_offset, int yaw_offset, double yaw_res){
        xy_offset_ = xy_offset;
        yaw_offset_ = yaw_offset;
        yaw_resolution_ = yaw_res;
    }

    /**
     * @brief 多候选位姿同步ICP配准，通过搜索多个初始位姿提高配准成功率
     * 
     * 该函数实现基于多初始候选位姿的鲁棒ICP配准策略：
     * 1. 候选位姿生成：在初始位姿周围生成多个候选位姿
     * 2. 并行粗配准：对所有候选位姿进行粗配准，选择最佳结果
     * 3. 精细配准：基于最佳粗配准结果进行高精度配准
     * 
     * @param source 输入的源点云（待配准点云）
     * @param init_guess 初始位姿估计（4x4变换矩阵）
     * @return Eigen::Matrix4d 最终配准结果的变换矩阵
     *                         - 成功：返回精配准的最终变换矩阵
     *                         - 失败：返回零矩阵（Eigen::Matrix4d::Zero()）
     * 
     * @note 搜索策略：
     *       - X/Y方向：在初始位置±xy_offset_范围内搜索（3×3网格）
     *       - Yaw角度：在初始角度±yaw_offset_×yaw_resolution_范围内搜索
     *       - Roll/Pitch：保持初始值不变
     *       - 总候选数量：3×3×(2×yaw_offset_+1)
     * 
     * @details 执行流程：
     *          1. 解析初始位姿的位置和姿态（RPY）
     *          2. 生成搜索网格内的所有候选位姿
     *          3. 对源点云进行预处理（滤波+法向量计算）
     *          4. 遍历所有候选位姿进行粗配准
     *          5. 选择适应度得分最佳的粗配准结果
     *          6. 基于最佳粗配准结果进行精配准
     * 
     * @warning 配准可能失败的情况：
     *          - 所有候选位姿的粗配准均未收敛
     *          - 所有粗配准适应度得分均超过2×thresh_
     *          - 精配准未收敛
     *          - 精配准适应度得分超过thresh_
     * 
     * @performance 计算复杂度与候选位姿数量成正比，适用于初始位姿不确定性较大的场景
     */
    Eigen::Matrix4d IcpLocalizer::multi_align_sync(pcl::PointCloud<pcl::PointXYZI>::Ptr source, Eigen::Matrix4d init_guess)
    {
        success_ = false;  // 初始化配准状态为失败
        
        // === 第一步：解析初始位姿信息 ===
        Eigen::Vector3d xyz = init_guess.block<3, 1>(0, 3);        // 提取初始位置
        Eigen::Matrix3d rotation = init_guess.block<3, 3>(0, 0);   // 提取初始旋转矩阵
        Eigen::Vector3d rpy = rotate2rpy(rotation);                // 转换为Roll-Pitch-Yaw角度
        std::cout << "[ICP] Initial guess: pos=(" << xyz.transpose() << "), rpy=(" << rpy.transpose() << ")" << std::endl;

        // 预计算Roll和Pitch的角轴表示（保持不变）
        Eigen::AngleAxisf rollAngle(rpy(0), Eigen::Vector3f::UnitX());
        Eigen::AngleAxisf pitchAngle(rpy(1), Eigen::Vector3f::UnitY());
        
        // === 第二步：生成候选位姿集合 ===
        std::vector<Eigen::Matrix4f> candidates;
        Eigen::Matrix4f temp_pose;
        
        // 三重循环生成搜索网格内的所有候选位姿
        for (int i = -3; i <= 3; i++)           // X方向：-xy_offset_, 0, +xy_offset_
        {
            for (int j = -3; j <= 3; j++)       // Y方向：-xy_offset_, 0, +xy_offset_
            {
                for (int k = -yaw_offset_; k <= yaw_offset_; k++)  // Yaw方向：角度步进搜索
                {
                    // 构造候选位置（Z坐标保持不变）
                    Eigen::Vector3f pos(xyz(0) + i * xy_offset_, xyz(1) + j * xy_offset_, xyz(2));
                    
                    // 构造候选Yaw角度
                    Eigen::AngleAxisf yawAngle(rpy(2) + k * yaw_resolution_, Eigen::Vector3f::UnitZ());
                    
                    // 组装4x4变换矩阵
                    temp_pose.setIdentity();
                    temp_pose.block<3, 3>(0, 0) = (rollAngle * pitchAngle * yawAngle).toRotationMatrix();
                    temp_pose.block<3, 1>(0, 3) = pos;
                    candidates.push_back(temp_pose);
                }
            }
        }
        std::cout << "[ICP] Candidate poses: " << candidates.size() << std::endl;
        // === 第三步：源点云预处理 ===
        pcl::PointCloud<pcl::PointXYZI>::Ptr rough_source(new pcl::PointCloud<pcl::PointXYZI>);
        pcl::PointCloud<pcl::PointXYZI>::Ptr refine_source(new pcl::PointCloud<pcl::PointXYZI>);

        // 分别进行粗滤波和精滤波
        voxel_rough_filter_.setInputCloud(source);
        voxel_rough_filter_.filter(*rough_source);
        voxel_refine_filter_.setInputCloud(source);
        voxel_refine_filter_.filter(*refine_source);

        // 为滤波后的点云计算法向量
        PointCloudXYZI::Ptr rough_source_norm = addNorm(rough_source);
        PointCloudXYZI::Ptr refine_source_norm = addNorm(refine_source);
        PointCloudXYZI::Ptr align_point(new PointCloudXYZI);

        // === 第四步：多候选位姿粗配准 ===
        Eigen::Matrix4f best_rough_transform;
        double best_rough_score = 10.0;  // 初始化为较大值
        bool rough_converge = false;
        
        // 遍历所有候选位姿进行粗配准
        for (Eigen::Matrix4f &init_pose : candidates)
        {
            icp_rough_.setInputSource(rough_source_norm);
            icp_rough_.align(*align_point, init_pose);
            
            // 检查粗配准收敛性
            if (!icp_rough_.hasConverged())
                continue;
                
            double rough_score = icp_rough_.getFitnessScore();
            
            // 过滤适应度得分过高的结果
            if (rough_score > 2 * thresh_)
                continue;
                
            // 更新最佳粗配准结果
            if (rough_score < best_rough_score)
            {
                best_rough_score = rough_score;
                rough_converge = true;
                best_rough_transform = icp_rough_.getFinalTransformation();
            }
        }

        // 检查是否找到有效的粗配准结果
        if (!rough_converge) {
            std::cout << "[ICP] No valid rough alignment found." << std::endl;
            return Eigen::Matrix4d::Zero();
        }
            std::cout << "[ICP] Best rough score: " << best_rough_score << std::endl;

        icp_refine_.setInputSource(refine_source_norm);
        icp_refine_.align(*align_point, best_rough_transform);
        score_ = icp_refine_.getFitnessScore();

        std::cout << "[ICP] Refine score: " << score_ << std::endl;

        if (!icp_refine_.hasConverged()) {
            std::cout << "[ICP] Refine alignment failed to converge." << std::endl;
            return Eigen::Matrix4d::Zero();
        }
        if (score_ > thresh_) {
            std::cout << "[ICP] Refine alignment score too high." << std::endl;
            return Eigen::Matrix4d::Zero();
        }

        std::cout << "[ICP] Alignment SUCCESS." << std::endl;
        success_ = true;
        return icp_refine_.getFinalTransformation().cast<double>();
    }
}