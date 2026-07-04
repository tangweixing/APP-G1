#include "lio_builder/lio_builder.h"

// #include <chrono>
namespace fastlio
{
    /**
     * @brief
     */
    LIOBuilder::LIOBuilder(LioParams &params) : params_(params)
    { // 初始化ESIKF
        kf_ = std::make_shared<esekfom::esekf<state_ikfom, 12, input_ikfom>>();
        std::vector<double> epsi(23, 0.001);
        kf_->init_dyn_share(
            get_f, df_dx, df_dw,
            [this](state_ikfom &s, esekfom::dyn_share_datastruct<double> &ekfom_data)
            { sharedUpdateFunc(s, ekfom_data); },
            params.esikf_max_iteration, epsi.data());

        // 初始化IMUProcessor
        imu_processor_ = std::make_shared<IMUProcessor>(kf_);
        imu_processor_->setCov(params.imu_gyro_cov, params.imu_acc_cov, params.imu_gyro_bias_cov, params.imu_acc_bias_cov);
        Eigen::Matrix3d rot_ext;
        Eigen::Vector3d pos_ext;
        rot_ext << params.imu_ext_rot[0], params.imu_ext_rot[1], params.imu_ext_rot[2],
            params.imu_ext_rot[3], params.imu_ext_rot[4], params.imu_ext_rot[5],
            params.imu_ext_rot[6], params.imu_ext_rot[7], params.imu_ext_rot[8];
        pos_ext << params.imu_ext_pos[0], params.imu_ext_pos[1], params.imu_ext_pos[2];
        imu_processor_->setExtParams(rot_ext, pos_ext);
        imu_processor_->setAlignGravity(params.align_gravity);
        // 初始化KDTree
        ikdtree_ = std::make_shared<KD_TREE<PointType>>();
        ikdtree_->set_downsample_param(params.resolution);
        // 初始化点云采样器
        down_size_filter_.setLeafSize(params.resolution, params.resolution, params.resolution);

        // 初始化local_map
        local_map_.cube_len = params.cube_len;
        local_map_.det_range = params.det_range;

        extrinsic_est_en_ = params.extrinsic_est_en;

        cloud_down_lidar_.reset(new PointCloudXYZI);

        cloud_down_world_.reset(new PointCloudXYZI(NUM_MAX_POINTS, 1));
        norm_vec_.reset(new PointCloudXYZI(NUM_MAX_POINTS, 1));

        effect_cloud_lidar_.reset(new PointCloudXYZI(NUM_MAX_POINTS, 1));
        effect_norm_vec_.reset(new PointCloudXYZI(NUM_MAX_POINTS, 1));

        nearest_points_.resize(NUM_MAX_POINTS);
        point_selected_flag_.resize(NUM_MAX_POINTS, false);
    }

    /**
     * @brief 将点云转换到世界坐标系下
     * @param cloud: lidar系下的点云
     *
     */
    PointCloudXYZI::Ptr LIOBuilder::transformToWorld(const PointCloudXYZI::Ptr cloud)
    {
        PointCloudXYZI::Ptr cloud_world(new PointCloudXYZI);
        Eigen::Matrix3d rot = kf_->get_x().rot.toRotationMatrix();
        Eigen::Vector3d pos = kf_->get_x().pos;
        Eigen::Matrix3d rot_ext = kf_->get_x().offset_R_L_I.toRotationMatrix();
        Eigen::Vector3d pos_ext = kf_->get_x().offset_T_L_I;
        cloud_world->reserve(cloud->size());
        for (auto &p : cloud->points)
        {
            Eigen::Vector3d point(p.x, p.y, p.z);
            point = rot * (rot_ext * point + pos_ext) + pos;
            PointType p_world;
            p_world.x = point(0);
            p_world.y = point(1);
            p_world.z = point(2);
            p_world.intensity = p.intensity;
            cloud_world->points.push_back(p_world);
        }
        return cloud_world;
    }

    /**
     * @brief 执行一次 LIO（激光惯导）建图与状态更新流程
     * 
     * 此函数完成以下核心任务：
     * 
     * 1. 对输入的多传感器测量数据 `meas`（包含 IMU 与雷达）进行处理：
     *    - 调用 imu_processor_ 对 IMU 数据进行预积分，完成去畸变点云生成。
     *    - 若 IMU 数据不足或处理失败，函数直接返回。
     * 
     * 2. 对去畸变后的点云 `cloud_undistorted_lidar_` 进行下采样滤波，减小点数：
     *    - 使用体素滤波器 `down_size_filter_` 得到 `cloud_down_lidar_`。
     * 
     * 3. 初始化地图：
     *    - 若当前状态为 `INITIALIZE`，则将下采样点云转换到世界坐标系并建立 `ikdtree_` 地图索引结构。
     *    - 状态切换为 `MAPPING` 后返回，不再进行后续步骤。
     * 
     * 4. 正式建图流程（仅在状态为 `MAPPING` 时执行）：
     *    - 调用 `trimMap()` 对地图进行局部修剪（例如移除远离当前位置的点）。
     *    - 使用卡尔曼滤波器 `kf_` 执行非线性状态估计更新（`update_iterated_dyn_share_modified`）。
     *    - 调用 `increaseMap()` 将当前帧点云更新到地图中。
     */
    void LIOBuilder::mapping(const MeasureGroup &meas)
    {
        if (!imu_processor_->operator()(meas, cloud_undistorted_lidar_))
            return;

        down_size_filter_.setInputCloud(cloud_undistorted_lidar_);
        down_size_filter_.filter(*cloud_down_lidar_);

        if (status == Status::INITIALIZE)
        {
            // 初始化ikd_tree
            PointCloudXYZI::Ptr point_world = transformToWorld(cloud_down_lidar_);
            ikdtree_->Build(point_world->points);
            status = Status::MAPPING;
            return;
        }

        trimMap();
        // auto tic = std::chrono::system_clock::now();
        double solve_H_time = 0;
        kf_->update_iterated_dyn_share_modified(0.001, solve_H_time);
        // auto toc = std::chrono::system_clock::now();
        // std::chrono::duration<double> duration = toc - tic;
        // std::cout << duration.count() * 1000 << std::endl;
        increaseMap();
    }

    /**
     * @brief 根据当前激光雷达位置，动态裁剪和维护局部地图范围中的点云（ikdtree）。
     * 
     * 功能说明：
     * - 本函数根据激光雷达当前在世界坐标系中的位置，维护一个固定大小的局部地图。
     * - 当雷达靠近局部地图边缘时，自动移动局部地图窗口，并从 ikdtree 中移除移出窗口之外的点。
     * - 有助于限制地图大小，提高建图效率，适用于滑动窗口地图或稀疏建图场景。
     * 
     * 处理流程：
     * 1. 若局部地图尚未初始化，则以当前位置为中心初始化一个立方体范围作为局部地图；
     * 2. 若地图已初始化，则判断当前雷达位置是否靠近边缘：
     *    - 若靠近边缘（小于 `move_thresh * det_range`），则标记为需要移动地图；
     *    - 按移动距离 `mov_dist` 更新地图边界（局部地图向外平移）；
     *    - 记录哪些旧区域需要从 `ikdtree_` 中删除（`cub_to_rm`）；
     * 3. 最后调用 `ikdtree_->Delete_Point_Boxes()` 删除旧区域中的点，保持地图精简。
     */

    void LIOBuilder::trimMap()
    {
        // === 1. 清空即将移除的地图立方体列表 ===
        local_map_.cub_to_rm.clear();

        // === 2. 获取当前激光雷达在世界坐标系中的位置 ===
        state_ikfom state = kf_->get_x();
        Eigen::Vector3d pos_lidar = state.pos + state.rot.toRotationMatrix() * state.offset_T_L_I;

        // === 3. 若局部地图未初始化，初始化为以当前激光雷达为中心的立方体 ===
        if (!local_map_.is_initialed)
        {
            for (int i = 0; i < 3; i++)
            {
                local_map_.local_map_corner.vertex_min[i] = pos_lidar[i] - local_map_.cube_len / 2.0;//局部地图各轴的角点
                local_map_.local_map_corner.vertex_max[i] = pos_lidar[i] + local_map_.cube_len / 2.0;
            }
            local_map_.is_initialed = true;
            return;
        }

        // === 4. 判断当前位置是否靠近局部地图边界，决定是否需要移动地图 ===
        float dist_to_map_edge[3][2];   // 存储每个轴到边界的距离 [min, max]
        bool need_move = false;

        // local_map_.move_thresh	一个系数，表示“靠近边界”的灵敏度（一般为 0.2~0.5 之间的浮点数）
        // local_map_.det_range	一个距离值（单位：米），表示局部地图每次移动时检测的边界范围
        // det_thresh	计算出的实际阈值，当激光雷达距离边界小于该值时就需要“搬家”

        double det_thresh = local_map_.move_thresh * local_map_.det_range;

        for (int i = 0; i < 3; i++)
        {
            dist_to_map_edge[i][0] = fabs(pos_lidar(i) - local_map_.local_map_corner.vertex_min[i]);
            dist_to_map_edge[i][1] = fabs(pos_lidar(i) - local_map_.local_map_corner.vertex_max[i]);

            if (dist_to_map_edge[i][0] <= det_thresh || dist_to_map_edge[i][1] <= det_thresh)
                need_move = true;
        }

        // === 5. 如果不需要移动地图，直接返回 ===
        if (!need_move)
            return;

        // === 6. 计算地图应移动的距离 ===
        BoxPointType new_corner, temp_corner;
        new_corner = local_map_.local_map_corner;

        float mov_dist = std::max(
            (local_map_.cube_len - 2.0 * local_map_.move_thresh * local_map_.det_range) * 0.5 * 0.9,
            double(local_map_.det_range * (local_map_.move_thresh - 1)));

        // === 7. 沿各个方向平移局部地图，并记录要移除的旧区域 ===
        for (int i = 0; i < 3; i++)
        {
            temp_corner = local_map_.local_map_corner;

            if (dist_to_map_edge[i][0] <= det_thresh)
            {
                // 向负方向移动地图
                new_corner.vertex_max[i] -= mov_dist;
                new_corner.vertex_min[i] -= mov_dist;

                // 记录被移出的区域
                temp_corner.vertex_min[i] = local_map_.local_map_corner.vertex_max[i] - mov_dist;
                local_map_.cub_to_rm.push_back(temp_corner);
            }
            else if (dist_to_map_edge[i][1] <= det_thresh)
            {
                // 向正方向移动地图
                new_corner.vertex_max[i] += mov_dist;
                new_corner.vertex_min[i] += mov_dist;

                // 记录被移出的区域
                temp_corner.vertex_max[i] = local_map_.local_map_corner.vertex_min[i] + mov_dist;
                local_map_.cub_to_rm.push_back(temp_corner);
            }
        }

        // === 8. 更新当前局部地图的边界信息 ===
        local_map_.local_map_corner = new_corner;

        // === 9. 强制清理 ikdtree 中被标记为历史的点云（可能用于更新） ===
        PointVector points_history;
        ikdtree_->acquire_removed_points(points_history);

        // === 10. 从 ikdtree 中删除被移出局部地图的点云块 ===
        if (!local_map_.cub_to_rm.empty())
            ikdtree_->Delete_Point_Boxes(local_map_.cub_to_rm);

        return;
    }


    /**
     * @brief 将当前帧降采样后的点云融合到全局地图（ikdtree）中。
     * 
     * 该函数会根据当前帧的点云与历史地图中的近邻点分布情况判断哪些点需要添加到地图中：
     * - 若点周围无近邻或不满足体素内采样密度要求，则添加进地图；
     * - 部分点不需降采样，直接加入；
     * 最终更新全局地图 ikdtree。
     */

    void LIOBuilder::increaseMap()
    {
        if (status == Status::INITIALIZE)
            return;
        if (cloud_down_lidar_->empty())
            return;

        int size = cloud_down_lidar_->size();

        PointVector point_to_add;
        PointVector point_no_need_downsample;

        point_to_add.reserve(size);
        point_no_need_downsample.reserve(size);

        state_ikfom state = kf_->get_x();
        for (int i = 0; i < size; i++)
        {
            const PointType &p = cloud_down_lidar_->points[i];
            Eigen::Vector3d point(p.x, p.y, p.z);
            point = state.rot.toRotationMatrix() * (state.offset_R_L_I.toRotationMatrix() * point + state.offset_T_L_I) + state.pos;
            cloud_down_world_->points[i].x = point(0);
            cloud_down_world_->points[i].y = point(1);
            cloud_down_world_->points[i].z = point(2);
            cloud_down_world_->points[i].intensity = cloud_down_lidar_->points[i].intensity;
            // 如果该点附近没有近邻点则需要添加到地图中
            if (nearest_points_[i].empty())
            {
                point_to_add.push_back(cloud_down_world_->points[i]);
                continue;
            }

            const PointVector &points_near = nearest_points_[i];
            bool need_add = true;
            PointType downsample_result, mid_point;
            mid_point.x = std::floor(cloud_down_world_->points[i].x / params_.resolution) * params_.resolution + 0.5 * params_.resolution;
            mid_point.y = std::floor(cloud_down_world_->points[i].y / params_.resolution) * params_.resolution + 0.5 * params_.resolution;
            mid_point.z = std::floor(cloud_down_world_->points[i].z / params_.resolution) * params_.resolution + 0.5 * params_.resolution;

            // 如果该点所在的voxel没有点，则直接加入地图，且不需要降采样
            if (fabs(points_near[0].x - mid_point.x) > 0.5 * params_.resolution && fabs(points_near[0].y - mid_point.y) > 0.5 * params_.resolution && fabs(points_near[0].z - mid_point.z) > 0.5 * params_.resolution)
            {
                point_no_need_downsample.push_back(cloud_down_world_->points[i]);
                continue;
            }
            float dist = sq_dist(cloud_down_world_->points[i], mid_point);

            for (int readd_i = 0; readd_i < NUM_MATCH_POINTS; readd_i++)
            {
                // 如果该点的近邻点较少，则需要加入到地图中
                if (points_near.size() < NUM_MATCH_POINTS)
                    break;
                // 如果该点的近邻点距离voxel中心点的距离比该点距离voxel中心点更近，则不需要加入该点
                if (sq_dist(points_near[readd_i], mid_point) < dist)
                {
                    need_add = false;
                    break;
                }
            }
            if (need_add)
                point_to_add.push_back(cloud_down_world_->points[i]);
        }
        int add_point_size = ikdtree_->Add_Points(point_to_add, true);
        ikdtree_->Add_Points(point_no_need_downsample, false);
    }

    /**
     * @brief
     */
    void LIOBuilder::sharedUpdateFunc(state_ikfom &state, esekfom::dyn_share_datastruct<double> &share_data)
    {
        int size = cloud_down_lidar_->size();
#ifdef MP_EN
        omp_set_num_threads(MP_PROC_NUM);
#pragma omp parallel for

#endif
        for (int i = 0; i < size; i++)
        {
            PointType &point_body = cloud_down_lidar_->points[i];
            PointType &point_world = cloud_down_world_->points[i];
            Eigen::Vector3d point_body_vec(point_body.x, point_body.y, point_body.z);
            Eigen::Vector3d point_world_vec = state.rot.toRotationMatrix() * (state.offset_R_L_I.toRotationMatrix() * point_body_vec + state.offset_T_L_I) + state.pos;
            point_world.x = point_world_vec(0);
            point_world.y = point_world_vec(1);
            point_world.z = point_world_vec(2);
            point_world.intensity = point_body.intensity;

            std::vector<float> point_sq_dist(NUM_MATCH_POINTS);
            auto &points_near = nearest_points_[i];
            if (share_data.converge)
            {
                ikdtree_->Nearest_Search(point_world, NUM_MATCH_POINTS, points_near, point_sq_dist);
                if (points_near.size() >= NUM_MATCH_POINTS && point_sq_dist[NUM_MATCH_POINTS - 1] <= 5)
                    point_selected_flag_[i] = true;
                else
                    point_selected_flag_[i] = false;
            }
            if (!point_selected_flag_[i])
                continue;

            Eigen::Vector4d pabcd;
            point_selected_flag_[i] = false;

            // 估计平面法向量，同时计算点面距离，计算的值存入intensity
            if (esti_plane(pabcd, points_near, 0.1))
            {
                double pd2 = pabcd(0) * point_world_vec(0) + pabcd(1) * point_world_vec(1) + pabcd(2) * point_world_vec(2) + pabcd(3);
                // 和点面距离正相关，和点的远近距离负相关
                double s = 1 - 0.9 * std::fabs(pd2) / std::sqrt(point_body_vec.norm());
                if (s > 0.9)
                {
                    point_selected_flag_[i] = true;
                    norm_vec_->points[i].x = pabcd(0);
                    norm_vec_->points[i].y = pabcd(1);
                    norm_vec_->points[i].z = pabcd(2);
                    norm_vec_->points[i].intensity = pd2;
                }
            }
        }

        int effect_feat_num = 0;
        for (int i = 0; i < size; i++)
        {
            if (!point_selected_flag_[i])
                continue;
            effect_cloud_lidar_->points[effect_feat_num] = cloud_down_lidar_->points[i];
            effect_norm_vec_->points[effect_feat_num] = norm_vec_->points[i];
            effect_feat_num++;
        }
        if (effect_feat_num < 1)
        {
            share_data.valid = false;
            ROS_INFO("NO Effective Points!");
            return;
        }

        share_data.h_x = Eigen::MatrixXd::Zero(effect_feat_num, 12);
        share_data.h.resize(effect_feat_num);

        for (int i = 0; i < effect_feat_num; i++)
        {
            const PointType &laser_p = effect_cloud_lidar_->points[i];
            const PointType &norm_p = effect_norm_vec_->points[i];
            Eigen::Vector3d laser_p_vec(laser_p.x, laser_p.y, laser_p.z);
            Eigen::Vector3d norm_vec(norm_p.x, norm_p.y, norm_p.z);
            Eigen::Vector3d temp_vec = state.offset_R_L_I.toRotationMatrix() * laser_p_vec + state.offset_T_L_I;
            Eigen::Matrix3d temp_mat;
            temp_mat << SKEW_SYM_MATRX(temp_vec);
            Eigen::Matrix<double, 1, 3> B = -norm_vec.transpose() * state.rot.toRotationMatrix() * temp_mat;
            share_data.h_x.block<1, 3>(i, 0) = norm_vec.transpose();
            share_data.h_x.block<1, 3>(i, 3) = B;
            if (extrinsic_est_en_)
            {
                temp_mat << SKEW_SYM_MATRX(laser_p_vec);
                Eigen::Matrix<double, 1, 3> C = -norm_vec.transpose() * state.rot.toRotationMatrix() * state.offset_R_L_I.toRotationMatrix() * temp_mat;
                Eigen::Matrix<double, 1, 3> D = norm_vec.transpose() * state.rot.toRotationMatrix();
                share_data.h_x.block<1, 3>(i, 6) = C;
                share_data.h_x.block<1, 3>(i, 9) = D;
            }
            share_data.h(i) = -norm_p.intensity;
        }
    }

    PointCloudXYZI::Ptr LIOBuilder::cloudUndistortedBody()
    {
        PointCloudXYZI::Ptr cloud_undistorted_body(new PointCloudXYZI);
        Eigen::Matrix3d rot = kf_->get_x().offset_R_L_I.toRotationMatrix();
        Eigen::Vector3d pos = kf_->get_x().offset_T_L_I;
        cloud_undistorted_body->reserve(cloud_undistorted_lidar_->size());
        for (auto &p : cloud_undistorted_lidar_->points)
        {
            Eigen::Vector3d point(p.x, p.y, p.z);
            point = rot * point + pos;
            PointType p_body;
            p_body.x = point(0);
            p_body.y = point(1);
            p_body.z = point(2);
            p_body.intensity = p.intensity;
            cloud_undistorted_body->points.push_back(p_body);
        }
        return cloud_undistorted_body;
    }

    PointCloudXYZI::Ptr LIOBuilder::cloudDownBody()
    {
        PointCloudXYZI::Ptr cloud_down_body(new PointCloudXYZI);
        Eigen::Matrix3d rot = kf_->get_x().offset_R_L_I.toRotationMatrix();
        Eigen::Vector3d pos = kf_->get_x().offset_T_L_I;
        cloud_down_body->reserve(cloud_down_lidar_->size());
        for (auto &p : cloud_down_lidar_->points)
        {
            Eigen::Vector3d point(p.x, p.y, p.z);
            point = rot * point + pos;
            PointType p_body;
            p_body.x = point(0);
            p_body.y = point(1);
            p_body.z = point(2);
            p_body.intensity = p.intensity;
            cloud_down_body->points.push_back(p_body);
        }
        return cloud_down_body;
    }
    
    void LIOBuilder::reset()
    {

        status = Status::INITIALIZE;
        imu_processor_->reset();
        state_ikfom state = kf_->get_x();
        state.rot.setIdentity();
        state.pos.setZero();
        state.vel.setZero();
        state.offset_R_L_I.setIdentity();
        state.offset_T_L_I.setZero();
        state.ba.setZero();
        state.bg.setZero();
        kf_->change_x(state);
        ikdtree_.reset(new KD_TREE<PointType>);
    }
}
