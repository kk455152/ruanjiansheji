/*==============================================================*/
/* DBMS name:      MySQL 8.0                                    */
/* Created on:     2026/6/1                                     */
/*==============================================================*/

DROP DATABASE IF EXISTS smart_speaker;

CREATE DATABASE smart_speaker
  DEFAULT CHARACTER SET utf8mb4
  COLLATE utf8mb4_0900_ai_ci;

USE smart_speaker;

SET FOREIGN_KEY_CHECKS = 0;
drop table if exists daily_stats;

drop table if exists action_dict;

drop table if exists admin_data_scope;

drop table if exists admin_auth_token;

drop table if exists admin_login_log;

drop table if exists admin_operation_log;

drop table if exists admin_permission;

drop table if exists admin_role;

drop table if exists admin_role_permission;

drop table if exists admin_user;

drop table if exists admin_user_role;

drop table if exists analytics_metric_daily;

drop table if exists auth_token;

drop table if exists battery_notice_setting;

drop table if exists data_job_task;

drop table if exists device;

drop table if exists device_bind_task;

drop table if exists device_firmware;

drop table if exists device_firmware_release;

drop table if exists device_firmware_release_device;

drop table if exists device_firmware_update_task;

drop table if exists device_log;

drop table if exists device_settings;

drop table if exists friendship;

drop table if exists high_risk_operation;

drop table if exists hot_ranking_daily;

drop table if exists listen_room;

drop table if exists listen_room_comment;

drop table if exists listen_room_member;

drop table if exists media_mapping;

drop table if exists music_service_binding;

drop table if exists music_service_permission;

drop table if exists play_history;

drop table if exists region_stats_daily;

drop table if exists sales_order;

drop table if exists sales_order_item;

drop table if exists security_event_log;

drop table if exists share_record;

drop table if exists system_backup_task;

drop table if exists system_config;

drop table if exists system_upgrade_package;

drop table if exists `user`;

drop table if exists user_activity_daily;

drop table if exists user_device_binding;

drop table if exists user_feedback;

drop table if exists user_feedback_process_log;

drop table if exists user_profile;

drop table if exists user_value_segment_daily;
/*==============================================================*/
/* Table: daily_stats                                           */
/*==============================================================*/
create table daily_stats
(
   stat_date            date not null,
   total_play_count     int not null,
   unique_song_count    int not null,
   unique_user_count    int not null,
   active_user_count    int not null,
   online_device_count  int not null,
   platform_wechat_count int not null,
   platform_qq_count    int not null,
   unique_device_count  int not null,
   total_play_duration_seconds bigint not null,
   avg_play_duration_seconds dec(10,2) not null,
   hottest_song_external_id varchar(100) not null,
   hottest_song_name    varchar(255) not null,
   hottest_artist       varchar(255) not null,
   hottest_play_count   int not null,
   new_user_count       int not null default 0,
   new_device_count     int not null default 0,
   total_sales_amount   decimal(12,2) not null default 0.00,
   generated_at         datetime not null,
   updated_at           datetime not null default CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP,
   primary key (stat_date)
);

/*==============================================================*/
/* Table: action_dict                                           */
/*==============================================================*/
create table action_dict
(
   action_id            int not null auto_increment,
   action_code          varchar(50) not null,
   action_name          varchar(100) not null,
   category             varchar(50) not null,
   primary key (action_id),
   unique key uk_action_dict_code (action_code)
);

/*==============================================================*/
/* Table: admin_auth_token                                      */
/*==============================================================*/
create table admin_auth_token
(
   token_id             bigint not null auto_increment,
   admin_id             bigint not null,
   token                varchar(512) not null,
   token_type           varchar(20) not null,
   login_type           varchar(30),
   ip_address           varchar(45),
   user_agent           varchar(500),
   status               varchar(20) not null,
   expires_at           datetime not null,
   revoked_at           datetime,
   created_at           datetime not null default CURRENT_TIMESTAMP,
   updated_at           datetime not null default CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP,
   primary key (token_id),
   unique key uk_admin_auth_token (token)
);

/*==============================================================*/
/* Table: admin_operation_log                                   */
/*==============================================================*/
create table admin_operation_log
(
   log_id               bigint not null auto_increment,
   admin_id             bigint,
   `action`             varchar(100) not null,
   module               varchar(100),
   operation_name       varchar(100),
   path                 varchar(255) not null,
   request_method       varchar(20),
   ip_address           varchar(45),
   user_agent           varchar(500),
   params               text,
   result_status        varchar(20),
   error_message        varchar(500),
   created_at           timestamp not null default CURRENT_TIMESTAMP,
   primary key (log_id)
);

/*==============================================================*/
/* Table: admin_user                                            */
/*==============================================================*/
create table admin_user
(
   admin_id             bigint not null auto_increment,
   username             varchar(50) not null,
   password_hash        varchar(255) not null,
   role                 varchar(20),
   created_at           datetime not null default CURRENT_TIMESTAMP,
   updated_at           datetime not null default CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP,
   last_login_at        datetime,
   status               tinyint not null,
   real_name            varchar(50),
   job_no               varchar(50),
   position             varchar(100),
   phone                varchar(20),
   email                varchar(100),
   wechat_open_id       varchar(100),
   avatar               varchar(512),
   is_super_admin       tinyint not null default 0,
   primary key (admin_id),
   unique key uk_admin_user_username (username),
   unique key uk_admin_user_job_no (job_no),
   unique key uk_admin_user_phone (phone),
   unique key uk_admin_user_email (email),
   unique key uk_admin_user_wechat_open_id (wechat_open_id)
);

/*==============================================================*/
/* Table: admin_role                                            */
/*==============================================================*/
create table admin_role
(
   role_id              bigint not null auto_increment,
   role_code            varchar(50) not null,
   role_name            varchar(100) not null,
   role_type            varchar(30) not null,
   description          varchar(500),
   status               varchar(20) not null,
   created_by           bigint,
   updated_by           bigint,
   created_at           datetime not null default CURRENT_TIMESTAMP,
   updated_at           datetime not null default CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP,
   primary key (role_id),
   unique key uk_admin_role_code (role_code)
);

/*==============================================================*/
/* Table: admin_permission                                      */
/*==============================================================*/
create table admin_permission
(
   permission_id        bigint not null auto_increment,
   permission_code      varchar(100) not null,
   permission_name      varchar(100) not null,
   module_code          varchar(100) not null,
   module_name          varchar(100) not null,
   permission_type      varchar(30) not null,
   parent_id            bigint,
   route_path           varchar(255),
   api_path             varchar(255),
   sort_no              int not null default 0,
   status               varchar(20) not null,
   created_at           datetime not null default CURRENT_TIMESTAMP,
   updated_at           datetime not null default CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP,
   primary key (permission_id),
   unique key uk_admin_permission_code (permission_code)
);

/*==============================================================*/
/* Table: admin_user_role                                       */
/*==============================================================*/
create table admin_user_role
(
   id                   bigint not null auto_increment,
   admin_id             bigint not null,
   role_id              bigint not null,
   assigned_by          bigint,
   assigned_at          datetime not null,
   primary key (id),
   unique key uk_admin_user_role (admin_id, role_id)
);

/*==============================================================*/
/* Table: admin_role_permission                                 */
/*==============================================================*/
create table admin_role_permission
(
   id                   bigint not null auto_increment,
   role_id              bigint not null,
   permission_id        bigint not null,
   granted_by           bigint,
   granted_at           datetime not null,
   primary key (id),
   unique key uk_admin_role_permission (role_id, permission_id)
);

/*==============================================================*/
/* Table: admin_data_scope                                      */
/*==============================================================*/
create table admin_data_scope
(
   scope_id             bigint not null auto_increment,
   admin_id             bigint,
   role_id              bigint,
   scope_type           varchar(30) not null,
   scope_code           varchar(100) not null,
   scope_name           varchar(100),
   can_view             tinyint not null default 1,
   can_edit             tinyint not null default 0,
   can_export           tinyint not null default 0,
   created_at           datetime not null default CURRENT_TIMESTAMP,
   updated_at           datetime not null default CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP,
   primary key (scope_id),
   unique key uk_admin_data_scope_admin (admin_id, scope_type, scope_code),
   unique key uk_admin_data_scope_role (role_id, scope_type, scope_code),
   constraint chk_admin_data_scope_owner check (
      (admin_id is not null and role_id is null)
      or (admin_id is null and role_id is not null)
   )
);

/*==============================================================*/
/* Table: admin_login_log                                       */
/*==============================================================*/
create table admin_login_log
(
   login_id             bigint not null auto_increment,
   admin_id             bigint,
   username             varchar(50) not null,
   login_type           varchar(30),
   ip_address           varchar(45),
   user_agent           varchar(500),
   login_status         varchar(20) not null,
   fail_reason          varchar(255),
   logged_at            datetime not null,
   primary key (login_id)
);

/*==============================================================*/
/* Table: security_event_log                                    */
/*==============================================================*/
create table security_event_log
(
   event_id             bigint not null auto_increment,
   admin_id             bigint,
   event_type           varchar(50) not null,
   event_level          varchar(20) not null,
   title                varchar(200) not null,
   content              text,
   ip_address           varchar(45),
   user_agent           varchar(500),
   handled_status       varchar(20) not null,
   handled_by           bigint,
   handled_at           datetime,
   created_at           datetime not null default CURRENT_TIMESTAMP,
   primary key (event_id)
);

/*==============================================================*/
/* Table: auth_token                                            */
/*==============================================================*/
create table auth_token
(
   auth_id              bigint not null auto_increment,
   user_id              bigint,
   platform_type        varchar(20) not null,
   access_token         text not null,
   refresh_token        varchar(512) not null,
   expires_at           datetime not null,
   primary key (auth_id),
   unique key uk_auth_token_user_platform (user_id, platform_type)
);

/*==============================================================*/
/* Table: battery_notice_setting                                */
/*==============================================================*/
create table battery_notice_setting
(
   notice_id            bigint not null auto_increment,
   device_id            bigint,
   low_battery_enabled  tinyint not null,
   threshold            int not null,
   full_charge_notice   tinyint not null,
   updated_at           datetime default CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP,
   primary key (notice_id),
   unique key uk_battery_notice_device (device_id)
);

/*==============================================================*/
/* Table: device                                                */
/*==============================================================*/
create table device
(
   device_id            bigint not null auto_increment,
   device_number        varchar(64) not null,
   model_name           varchar(50) not null,
   status               tinyint not null,
   last_active          datetime not null,
   firmware_version     varchar(50),
   created_at           datetime not null default CURRENT_TIMESTAMP,
   device_name          varchar(100),
   device_type          varchar(50) not null,
   online_status        varchar(20),
   ip_address           varchar(64),
   hardware_version     varchar(50),
   location             varchar(100),
   updated_at           datetime not null default CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP,
   primary key (device_id),
   unique key uk_device_number (device_number)
);

/*==============================================================*/
/* Table: device_bind_task                                      */
/*==============================================================*/
create table device_bind_task
(
   task_id              bigint not null auto_increment,
   user_id              bigint not null,
   device_sn            varchar(64) not null,
   wifi_name            varchar(100) not null,
   wifi_password        varchar(255),
   progress             int not null,
   current_step         varchar(100),
   status               varchar(20),
   error_message        varchar(255),
   device_id            bigint,
   created_at           datetime not null default CURRENT_TIMESTAMP,
   updated_at           datetime not null default CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP,
   finished_at          datetime,
   primary key (task_id),
   constraint chk_device_bind_task_progress check (progress between 0 and 100)
);

/*==============================================================*/
/* Table: device_firmware                                       */
/*==============================================================*/
create table device_firmware
(
   firmware_id          bigint not null auto_increment,
   model_name           varchar(50) not null,
   device_type          varchar(50) not null,
   hardware_version     varchar(50) not null default 'default',
   version              varchar(50) not null,
   version_code         int not null,
   file_url             varchar(512),
   file_md5             varchar(64),
   file_size            bigint,
   description          text,
   force_update         tinyint not null,
   status               varchar(20) not null,
   created_at           datetime not null default CURRENT_TIMESTAMP,
   updated_at           datetime not null default CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP,
   primary key (firmware_id),
   unique key uk_device_firmware_version (model_name, device_type, hardware_version, version_code)
);

/*==============================================================*/
/* Table: device_firmware_release                               */
/*==============================================================*/
create table device_firmware_release
(
   release_id           bigint not null auto_increment,
   release_no           varchar(64) not null,
   firmware_id          bigint not null,
   target_model_name    varchar(50),
   target_device_type   varchar(50),
   target_hardware_version varchar(50),
   release_scope        varchar(30) not null,
   total_device_count   int not null default 0,
   success_device_count int not null default 0,
   fail_device_count    int not null default 0,
   status               varchar(30) not null,
   admin_id             bigint,
   operator_name        varchar(100),
   scheduled_at         datetime,
   started_at           datetime,
   finished_at          datetime,
   created_at           datetime not null default CURRENT_TIMESTAMP,
   updated_at           datetime not null default CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP,
   primary key (release_id),
   unique key uk_firmware_release_no (release_no)
);

/*==============================================================*/
/* Table: device_firmware_release_device                        */
/*==============================================================*/
create table device_firmware_release_device
(
   id                   bigint not null auto_increment,
   release_id           bigint not null,
   device_id            bigint not null,
   status               varchar(30) not null,
   progress             int not null default 0,
   fail_reason          varchar(500),
   created_at           datetime not null default CURRENT_TIMESTAMP,
   updated_at           datetime not null default CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP,
   primary key (id),
   unique key uk_release_device (release_id, device_id),
   constraint chk_firmware_release_device_progress check (progress between 0 and 100)
);

/*==============================================================*/
/* Table: device_firmware_update_task                           */
/*==============================================================*/
create table device_firmware_update_task
(
   task_id              bigint not null auto_increment,
   task_no              varchar(64) not null,
   device_id            bigint not null,
   firmware_id          bigint,
   release_device_id    bigint,
   current_version      varchar(50),
   target_version       varchar(50) not null,
   status               varchar(30) not null,
   progress             int not null,
   fail_reason          varchar(500),
   admin_id             bigint,
   operator_name        varchar(100),
   started_at           datetime,
   finished_at          datetime,
   created_at           datetime not null default CURRENT_TIMESTAMP,
   updated_at           datetime not null default CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP,
   primary key (task_id),
   unique key uk_firmware_update_task_no (task_no),
   constraint chk_firmware_update_task_progress check (progress between 0 and 100)
);

/*==============================================================*/
/* Table: device_log                                            */
/*==============================================================*/
create table device_log
(
   log_id               bigint not null auto_increment,
   device_id            bigint,
   device_sn            varchar(64),
   device_name          varchar(100),
   device_type          varchar(50),
   device_model         varchar(100),
   log_type             varchar(50) not null,
   log_level            varchar(20) not null,
   title                varchar(200),
   content              text not null,
   event_code           varchar(100),
   trace_id             varchar(100),
   task_id              varchar(100),
   firmware_version     varchar(50),
   online_status        varchar(20),
   ip_address           varchar(64),
   network_type         varchar(50),
   location             varchar(100),
   request_url          varchar(512),
   request_method       varchar(20),
   request_id           varchar(100),
   response_code        int,
   response_message     varchar(500),
   admin_id             bigint,
   operator_name        varchar(100),
   operator_type        varchar(50),
   created_at           datetime not null default CURRENT_TIMESTAMP,
   updated_at           datetime not null default CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP,
   primary key (log_id)
);

/*==============================================================*/
/* Table: device_settings                                       */
/*==============================================================*/
create table device_settings
(
   setting_id           bigint not null auto_increment,
   device_id            bigint,
   volume_limit         int not null,
   night_mode_enabled   tinyint not null,
   night_start          time,
   night_end            time,
   auto_firmware_update tinyint not null,
   power_save_enabled   tinyint not null,
   updated_at           datetime not null default CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP,
   primary key (setting_id),
   unique key uk_device_settings_device (device_id)
);

/*==============================================================*/
/* Table: system_config                                         */
/*==============================================================*/
create table system_config
(
   config_id            bigint not null auto_increment,
   config_key           varchar(100) not null,
   config_value         text,
   config_type          varchar(30) not null,
   config_group         varchar(50) not null,
   config_name          varchar(100) not null,
   description          varchar(500),
   editable             tinyint not null default 1,
   updated_by           bigint,
   created_at           datetime not null default CURRENT_TIMESTAMP,
   updated_at           datetime not null default CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP,
   primary key (config_id),
   unique key uk_system_config_key (config_key)
);

/*==============================================================*/
/* Table: system_upgrade_package                                */
/*==============================================================*/
create table system_upgrade_package
(
   package_id           bigint not null auto_increment,
   package_no           varchar(64) not null,
   package_name         varchar(100) not null,
   version              varchar(50) not null,
   file_url             varchar(512) not null,
   file_md5             varchar(64),
   file_size            bigint,
   upgrade_type         varchar(30) not null,
   description          text,
   status               varchar(20) not null,
   uploaded_by          bigint,
   applied_by           bigint,
   applied_at           datetime,
   created_at           datetime not null default CURRENT_TIMESTAMP,
   updated_at           datetime not null default CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP,
   primary key (package_id),
   unique key uk_system_upgrade_package_no (package_no)
);

/*==============================================================*/
/* Table: system_backup_task                                    */
/*==============================================================*/
create table system_backup_task
(
   task_id              bigint not null auto_increment,
   task_no              varchar(64) not null,
   task_type            varchar(30) not null,
   backup_scope         varchar(100),
   file_url             varchar(512),
   file_size            bigint,
   status               varchar(30) not null,
   fail_reason          varchar(500),
   admin_id             bigint,
   started_at           datetime,
   finished_at          datetime,
   created_at           datetime not null default CURRENT_TIMESTAMP,
   updated_at           datetime not null default CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP,
   primary key (task_id),
   unique key uk_system_backup_task_no (task_no)
);

/*==============================================================*/
/* Table: data_job_task                                         */
/*==============================================================*/
create table data_job_task
(
   job_id               bigint not null auto_increment,
   job_no               varchar(64) not null,
   job_type             varchar(30) not null,
   business_type        varchar(50) not null,
   file_url             varchar(512),
   total_count          int not null default 0,
   success_count        int not null default 0,
   fail_count           int not null default 0,
   status               varchar(30) not null,
   fail_reason          varchar(500),
   admin_id             bigint,
   started_at           datetime,
   finished_at          datetime,
   created_at           datetime not null default CURRENT_TIMESTAMP,
   updated_at           datetime not null default CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP,
   primary key (job_id),
   unique key uk_data_job_task_no (job_no)
);

/*==============================================================*/
/* Table: high_risk_operation                                   */
/*==============================================================*/
create table high_risk_operation
(
   operation_id         bigint not null auto_increment,
   operation_no         varchar(64) not null,
   operation_type       varchar(50) not null,
   target_type          varchar(50) not null,
   target_id            varchar(100),
   request_params       text,
   risk_level           varchar(20) not null,
   approval_status      varchar(30) not null,
   requested_by         bigint not null,
   approved_by          bigint,
   approved_at          datetime,
   executed_at          datetime,
   result_status        varchar(30),
   result_message       varchar(500),
   created_at           datetime not null default CURRENT_TIMESTAMP,
   updated_at           datetime not null default CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP,
   primary key (operation_id),
   unique key uk_high_risk_operation_no (operation_no)
);

/*==============================================================*/
/* Table: friendship                                            */
/*==============================================================*/
create table friendship
(
   user_id_2            bigint not null,
   user_id_1            bigint not null,
   primary key (user_id_2, user_id_1)
);

/*==============================================================*/
/* Table: listen_room                                           */
/*==============================================================*/
create table listen_room
(
   room_id              bigint not null auto_increment,
   room_code            varchar(64) not null,
   owner_user_id        bigint not null,
   device_id            bigint,
   current_song_id      varchar(100),
   room_name            varchar(100),
   source_platform      varchar(20),
   status               varchar(20) not null,
   created_at           datetime not null default CURRENT_TIMESTAMP,
   ended_at             datetime,
   primary key (room_id),
   unique key uk_listen_room_code (room_code)
);

/*==============================================================*/
/* Table: listen_room_comment                                   */
/*==============================================================*/
create table listen_room_comment
(
   comment_id           bigint not null auto_increment,
   room_id              bigint not null,
   user_id              bigint not null,
   content              varchar(255) not null,
   created_at           datetime not null default CURRENT_TIMESTAMP,
   primary key (comment_id)
);

/*==============================================================*/
/* Table: listen_room_member                                    */
/*==============================================================*/
create table listen_room_member
(
   id                   bigint not null auto_increment,
   room_id              bigint not null,
   user_id              bigint not null,
   role                 varchar(20) not null,
   online_status        tinyint not null,
   joined_at            datetime not null,
   left_at              datetime,
   primary key (id),
   unique key uk_listen_room_member_user (room_id, user_id)
);

/*==============================================================*/
/* Table: media_mapping                                         */
/*==============================================================*/
create table media_mapping
(
   mapping_id           bigint not null auto_increment,
   user_id              bigint,
   song_title           varchar(255) not null,
   artist               varchar(100) not null,
   platform             varchar(20) not null,
   external_id          varchar(100) not null,
   cover_url            varchar(512) not null,
   primary key (mapping_id),
   unique key uk_media_mapping_external (user_id, platform, external_id)
);

/*==============================================================*/
/* Table: music_service_binding                                 */
/*==============================================================*/
create table music_service_binding
(
   binding_id           bigint not null auto_increment,
   user_id              bigint not null,
   service              varchar(20) not null,
   account_name         varchar(100),
   access_token         text,
   refresh_token        text,
   expires_at           datetime,
   sync_status          varchar(20) not null,
   bound_at             datetime not null,
   updated_at           datetime not null default CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP,
   primary key (binding_id),
   unique key uk_music_service_binding (user_id, service)
);

/*==============================================================*/
/* Table: music_service_permission                              */
/*==============================================================*/
create table music_service_permission
(
   permission_id        bigint not null auto_increment,
   user_id              bigint,
   service              varchar(20) not null,
   read_playlist        tinyint not null,
   sync_history         tinyint not null,
   personal_recommend   tinyint not null,
   updated_at           datetime not null default CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP,
   primary key (permission_id),
   unique key uk_music_service_permission (user_id, service)
);

/*==============================================================*/
/* Table: play_history                                          */
/*==============================================================*/
create table play_history
(
   history_id           bigint not null auto_increment,
   device_id            bigint not null,
   user_id              bigint,
   mapping_id           bigint,
   play_duration        bigint,
   created_at           datetime default CURRENT_TIMESTAMP,
   style                varchar(50),
   source_platform      varchar(20),
   primary key (history_id)
);

/*==============================================================*/
/* Table: region_stats_daily                                    */
/*==============================================================*/
create table region_stats_daily
(
   id                   bigint not null auto_increment,
   stat_date            date not null,
   region_level         varchar(20) not null,
   region_name          varchar(100) not null,
   user_count           int not null,
   active_user_count    int not null,
   device_count         int not null,
   order_count          int not null,
   sales_amount         decimal(12,2) not null,
   created_at           datetime not null default CURRENT_TIMESTAMP,
   updated_at           datetime not null default CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP,
   region_code          varchar(20) not null,
   primary key (id),
   unique key uk_region_stats_daily (stat_date, region_level, region_code)
);

/*==============================================================*/
/* Table: analytics_metric_daily                                */
/*==============================================================*/
create table analytics_metric_daily
(
   metric_id            bigint not null auto_increment,
   metric_date          date not null,
   scope_type           varchar(30) not null,
   scope_code           varchar(100) not null,
   metric_code          varchar(50) not null,
   metric_name          varchar(100) not null,
   metric_value         decimal(18,4) not null,
   metric_unit          varchar(20),
   compare_value        decimal(18,4),
   growth_rate          decimal(10,4),
   created_at           datetime not null default CURRENT_TIMESTAMP,
   updated_at           datetime not null default CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP,
   primary key (metric_id),
   unique key uk_metric_daily_scope (metric_date, scope_type, scope_code, metric_code)
);

/*==============================================================*/
/* Table: hot_ranking_daily                                     */
/*==============================================================*/
create table hot_ranking_daily
(
   ranking_id           bigint not null auto_increment,
   ranking_date         date not null,
   ranking_type         varchar(50) not null,
   scope_type           varchar(30) not null,
   scope_code           varchar(100) not null,
   rank_no              int not null,
   target_id            varchar(100),
   target_name          varchar(255) not null,
   target_category      varchar(100),
   metric_value         decimal(18,4) not null,
   metric_unit          varchar(20),
   created_at           datetime not null default CURRENT_TIMESTAMP,
   primary key (ranking_id),
   unique key uk_hot_ranking_daily (ranking_date, ranking_type, scope_type, scope_code, rank_no)
);

/*==============================================================*/
/* Table: user_value_segment_daily                              */
/*==============================================================*/
create table user_value_segment_daily
(
   id                   bigint not null auto_increment,
   stat_date            date not null,
   segment_code         varchar(50) not null,
   segment_name         varchar(100) not null,
   user_count           int not null,
   active_user_count    int not null,
   avg_play_count       decimal(10,2),
   avg_pay_amount       decimal(12,2),
   retention_rate       decimal(10,4),
   created_at           datetime not null default CURRENT_TIMESTAMP,
   updated_at           datetime not null default CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP,
   primary key (id),
   unique key uk_user_value_segment_daily (stat_date, segment_code)
);

/*==============================================================*/
/* Table: sales_order                                           */
/*==============================================================*/
create table sales_order
(
   order_id             bigint not null auto_increment,
   order_no             varchar(64) not null,
   user_id              bigint,
   device_id            bigint,
   order_amount         decimal(10,2) not null,
   pay_amount           decimal(10,2) not null,
   order_status         varchar(30) not null,
   pay_status           varchar(30) not null,
   province_code        varchar(20),
   province_name        varchar(100),
   city_code            varchar(20),
   city_name            varchar(100),
   paid_at              datetime,
   created_at           datetime default CURRENT_TIMESTAMP,
   updated_at           datetime default CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP,
   primary key (order_id),
   unique key uk_sales_order_no (order_no)
);

/*==============================================================*/
/* Table: sales_order_item                                      */
/*==============================================================*/
create table sales_order_item
(
   item_id              bigint not null auto_increment,
   order_id             bigint not null,
   user_id              bigint,
   device_id            bigint,
   product_name         varchar(100) not null,
   model_name           varchar(50),
   quantity             int not null,
   unit_price           decimal(10,2) not null,
   total_amount         decimal(10,2) not null,
   created_at           datetime not null default CURRENT_TIMESTAMP,
   primary key (item_id)
);

/*==============================================================*/
/* Table: share_record                                          */
/*==============================================================*/
create table share_record
(
   share_id             bigint not null auto_increment,
   user_id              bigint not null,
   song_id              varchar(100) not null,
   room_id              bigint,
   share_type           varchar(20) not null,
   share_url            varchar(512),
   image_url            varchar(512),
   expire_at            datetime,
   created_at           datetime not null default CURRENT_TIMESTAMP,
   primary key (share_id)
);

/*==============================================================*/
/* Table: user                                                  */
/*==============================================================*/
create table `user`
(
   user_id              bigint not null auto_increment,
   username             varchar(50) not null,
   password_hash        varchar(255) not null,
   phone                varchar(20),
   created_at           datetime default CURRENT_TIMESTAMP,
   nickname             varchar(100),
   avatar               varchar(512),
   email                varchar(100),
   status               varchar(20),
   last_login_at        datetime,
   updated_at           datetime not null default CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP,
   primary key (user_id),
   unique key uk_user_username (username),
   unique key uk_user_phone (phone),
   unique key uk_user_email (email)
);

/*==============================================================*/
/* Table: user_activity_daily                                   */
/*==============================================================*/
create table user_activity_daily
(
   id                   bigint not null auto_increment,
   stat_date            date not null,
   user_id              bigint not null,
   play_count           int not null,
   play_duration        bigint not null,
   active_count         int not null,
   is_active            tinyint not null,
   created_at           datetime not null default CURRENT_TIMESTAMP,
   last_active_at       datetime,
   updated_at           datetime not null default CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP,
   primary key (id),
   unique key uk_user_activity_daily (stat_date, user_id)
);

/*==============================================================*/
/* Table: user_device_binding                                   */
/*==============================================================*/
create table user_device_binding
(
   binding_id           bigint not null auto_increment,
   user_id              bigint not null,
   device_id            bigint not null,
   custom_device_name   varchar(50) binary not null,
   is_primary           tinyint not null,
   default_room         varchar(50),
   current_network      varchar(100),
   bind_time            datetime not null,
   primary key (binding_id),
   unique key uk_user_device (user_id, device_id)
);

/*==============================================================*/
/* Table: user_feedback                                         */
/*==============================================================*/
create table user_feedback
(
   content              text not null,
   feedback_id          bigint not null auto_increment,
   user_id              bigint,
   feedback_no          varchar(64),
   feedback_type        varchar(50) not null,
   title                varchar(200),
   contact              varchar(100),
   device_info          text,
   status               varchar(30) not null,
   priority             varchar(20) not null,
   star_rating          tinyint,
   rating_tags          varchar(255),
   admin_id             bigint,
   handler_name         varchar(100),
   reply_content        text,
   handled_at           datetime,
   closed_at            datetime,
   created_at           datetime not null default CURRENT_TIMESTAMP,
   updated_at           datetime not null default CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP,
   primary key (feedback_id),
   unique key uk_user_feedback_no (feedback_no),
   constraint chk_user_feedback_star_rating check (star_rating is null or star_rating between 1 and 5)
);

/*==============================================================*/
/* Table: user_feedback_process_log                             */
/*==============================================================*/
create table user_feedback_process_log
(
   log_id               bigint not null auto_increment,
   feedback_id          bigint,
   `action`             varchar(50),
   action_text          varchar(100),
   admin_id             bigint,
   operator_name        varchar(100),
   remark               varchar(500),
   created_at           datetime not null default CURRENT_TIMESTAMP,
   primary key (log_id)
);

/*==============================================================*/
/* Table: user_profile                                          */
/*==============================================================*/
create table user_profile
(
   profile_id           bigint not null auto_increment,
   user_id              bigint not null,
   nickname             varchar(100),
   email                varchar(100),
   gender               varchar(20),
   age                  int,
   age_range            varchar(20),
   province_code        varchar(20),
   province_name        varchar(100),
   city_code            varchar(20),
   city_name            varchar(100),
   active_level         varchar(20),
   value_level          varchar(20),
   bound_platforms      varchar(255),
   user_status          varchar(20) not null,
   created_at           datetime not null default CURRENT_TIMESTAMP,
   updated_at           datetime not null default CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP,
   primary key (profile_id),
   unique key uk_user_profile_user (user_id)
);

alter table admin_auth_token add constraint FK_Reference_37 foreign key (admin_id)
      references admin_user (admin_id) on delete restrict on update restrict;

alter table admin_operation_log add constraint FK_Reference_36 foreign key (admin_id)
      references admin_user (admin_id) on delete restrict on update restrict;

alter table admin_role add constraint fk_admin_role_created_by foreign key (created_by)
      references admin_user (admin_id) on delete restrict on update restrict;

alter table admin_role add constraint fk_admin_role_updated_by foreign key (updated_by)
      references admin_user (admin_id) on delete restrict on update restrict;

alter table admin_permission add constraint fk_admin_permission_parent foreign key (parent_id)
      references admin_permission (permission_id) on delete restrict on update restrict;

alter table admin_user_role add constraint fk_admin_user_role_admin foreign key (admin_id)
      references admin_user (admin_id) on delete restrict on update restrict;

alter table admin_user_role add constraint fk_admin_user_role_role foreign key (role_id)
      references admin_role (role_id) on delete restrict on update restrict;

alter table admin_user_role add constraint fk_admin_user_role_assigned_by foreign key (assigned_by)
      references admin_user (admin_id) on delete restrict on update restrict;

alter table admin_role_permission add constraint fk_admin_role_permission_role foreign key (role_id)
      references admin_role (role_id) on delete restrict on update restrict;

alter table admin_role_permission add constraint fk_admin_role_permission_permission foreign key (permission_id)
      references admin_permission (permission_id) on delete restrict on update restrict;

alter table admin_role_permission add constraint fk_admin_role_permission_granted_by foreign key (granted_by)
      references admin_user (admin_id) on delete restrict on update restrict;

alter table admin_data_scope add constraint fk_admin_data_scope_admin foreign key (admin_id)
      references admin_user (admin_id) on delete restrict on update restrict;

alter table admin_data_scope add constraint fk_admin_data_scope_role foreign key (role_id)
      references admin_role (role_id) on delete restrict on update restrict;

alter table admin_login_log add constraint fk_admin_login_log_admin foreign key (admin_id)
      references admin_user (admin_id) on delete restrict on update restrict;

alter table security_event_log add constraint fk_security_event_log_admin foreign key (admin_id)
      references admin_user (admin_id) on delete restrict on update restrict;

alter table security_event_log add constraint fk_security_event_log_handled_by foreign key (handled_by)
      references admin_user (admin_id) on delete restrict on update restrict;

alter table auth_token add constraint FK_Reference_13 foreign key (user_id)
      references `user` (user_id) on delete restrict on update restrict;

alter table battery_notice_setting add constraint FK_Reference_22 foreign key (device_id)
      references device (device_id) on delete restrict on update restrict;

alter table device_bind_task add constraint FK_Reference_31 foreign key (user_id)
      references `user` (user_id) on delete restrict on update restrict;

alter table device_bind_task add constraint fk_device_bind_task_device foreign key (device_id)
      references device (device_id) on delete restrict on update restrict;

alter table device_firmware_update_task add constraint FK_Reference_38 foreign key (device_id)
      references device (device_id) on delete restrict on update restrict;

alter table device_firmware_update_task add constraint FK_Reference_39 foreign key (firmware_id)
      references device_firmware (firmware_id) on delete restrict on update restrict;

alter table device_firmware_update_task add constraint fk_firmware_update_release_device foreign key (release_device_id)
      references device_firmware_release_device (id) on delete restrict on update restrict;

alter table device_firmware_update_task add constraint FK_Reference_40 foreign key (admin_id)
      references admin_user (admin_id) on delete restrict on update restrict;

alter table device_firmware_release add constraint fk_device_firmware_release_firmware foreign key (firmware_id)
      references device_firmware (firmware_id) on delete restrict on update restrict;

alter table device_firmware_release add constraint fk_device_firmware_release_admin foreign key (admin_id)
      references admin_user (admin_id) on delete restrict on update restrict;

alter table device_firmware_release_device add constraint fk_firmware_release_device_release foreign key (release_id)
      references device_firmware_release (release_id) on delete restrict on update restrict;

alter table device_firmware_release_device add constraint fk_firmware_release_device_device foreign key (device_id)
      references device (device_id) on delete restrict on update restrict;

alter table device_log add constraint FK_Reference_41 foreign key (device_id)
      references device (device_id) on delete restrict on update restrict;

alter table device_log add constraint FK_Reference_42 foreign key (admin_id)
      references admin_user (admin_id) on delete restrict on update restrict;

alter table device_settings add constraint FK_Reference_21 foreign key (device_id)
      references device (device_id) on delete restrict on update restrict;

alter table system_config add constraint fk_system_config_updated_by foreign key (updated_by)
      references admin_user (admin_id) on delete restrict on update restrict;

alter table system_upgrade_package add constraint fk_system_upgrade_uploaded_by foreign key (uploaded_by)
      references admin_user (admin_id) on delete restrict on update restrict;

alter table system_upgrade_package add constraint fk_system_upgrade_applied_by foreign key (applied_by)
      references admin_user (admin_id) on delete restrict on update restrict;

alter table system_backup_task add constraint fk_system_backup_task_admin foreign key (admin_id)
      references admin_user (admin_id) on delete restrict on update restrict;

alter table data_job_task add constraint fk_data_job_task_admin foreign key (admin_id)
      references admin_user (admin_id) on delete restrict on update restrict;

alter table high_risk_operation add constraint fk_high_risk_requested_by foreign key (requested_by)
      references admin_user (admin_id) on delete restrict on update restrict;

alter table high_risk_operation add constraint fk_high_risk_approved_by foreign key (approved_by)
      references admin_user (admin_id) on delete restrict on update restrict;

alter table friendship add constraint FK_Reference_12 foreign key (user_id_1)
      references `user` (user_id) on delete restrict on update restrict;

alter table friendship add constraint FK_Reference_19 foreign key (user_id_2)
      references `user` (user_id) on delete restrict on update restrict;

alter table listen_room add constraint FK_Reference_23 foreign key (owner_user_id)
      references `user` (user_id) on delete restrict on update restrict;

alter table listen_room add constraint FK_Reference_25 foreign key (device_id)
      references device (device_id) on delete restrict on update restrict;

alter table listen_room_comment add constraint FK_Reference_29 foreign key (room_id)
      references listen_room (room_id) on delete restrict on update restrict;

alter table listen_room_comment add constraint FK_Reference_30 foreign key (user_id)
      references `user` (user_id) on delete restrict on update restrict;

alter table listen_room_member add constraint FK_Reference_24 foreign key (room_id)
      references listen_room (room_id) on delete restrict on update restrict;

alter table listen_room_member add constraint FK_Reference_26 foreign key (user_id)
      references `user` (user_id) on delete restrict on update restrict;

alter table media_mapping add constraint FK_Reference_14 foreign key (user_id)
      references `user` (user_id) on delete restrict on update restrict;

alter table music_service_binding add constraint FK_Reference_33 foreign key (user_id)
      references `user` (user_id) on delete restrict on update restrict;

alter table music_service_permission add constraint FK_Reference_32 foreign key (user_id)
      references `user` (user_id) on delete restrict on update restrict;

alter table play_history add constraint FK_Reference_16 foreign key (user_id)
      references `user` (user_id) on delete restrict on update restrict;

alter table play_history add constraint FK_Reference_18 foreign key (device_id)
      references device (device_id) on delete restrict on update restrict;

alter table play_history add constraint FK_Reference_35 foreign key (mapping_id)
      references media_mapping (mapping_id) on delete restrict on update restrict;

alter table sales_order add constraint FK_Reference_45 foreign key (user_id)
      references `user` (user_id) on delete restrict on update restrict;

alter table sales_order add constraint FK_Reference_46 foreign key (device_id)
      references device (device_id) on delete restrict on update restrict;

alter table sales_order_item add constraint FK_Reference_47 foreign key (order_id)
      references sales_order (order_id) on delete restrict on update restrict;

alter table sales_order_item add constraint FK_Reference_48 foreign key (user_id)
      references `user` (user_id) on delete restrict on update restrict;

alter table sales_order_item add constraint FK_Reference_49 foreign key (device_id)
      references device (device_id) on delete restrict on update restrict;

alter table share_record add constraint FK_Reference_27 foreign key (user_id)
      references `user` (user_id) on delete restrict on update restrict;

alter table share_record add constraint FK_Reference_28 foreign key (room_id)
      references listen_room (room_id) on delete restrict on update restrict;

alter table user_activity_daily add constraint FK_Reference_51 foreign key (user_id)
      references `user` (user_id) on delete restrict on update restrict;

alter table user_device_binding add constraint FK_Reference_8 foreign key (device_id)
      references device (device_id) on delete restrict on update restrict;

alter table user_device_binding add constraint FK_Reference_9 foreign key (user_id)
      references `user` (user_id) on delete restrict on update restrict;

alter table user_feedback add constraint FK_Reference_11 foreign key (user_id)
      references `user` (user_id) on delete restrict on update restrict;

alter table user_feedback add constraint fk_user_feedback_admin foreign key (admin_id)
      references admin_user (admin_id) on delete restrict on update restrict;

alter table user_feedback_process_log add constraint FK_Reference_43 foreign key (feedback_id)
      references user_feedback (feedback_id) on delete restrict on update restrict;

alter table user_feedback_process_log add constraint FK_Reference_44 foreign key (admin_id)
      references admin_user (admin_id) on delete restrict on update restrict;

alter table user_profile add constraint FK_Reference_50 foreign key (user_id)
      references `user` (user_id) on delete restrict on update restrict;

SET FOREIGN_KEY_CHECKS = 1;


