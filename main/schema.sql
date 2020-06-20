create database coverityscanV2;
use coverityscanV2;

create table alert_type
(
    id       int auto_increment
        primary key,
    type     varchar(255) null,
    impact   varchar(255) null,
    category varchar(255) null,
    constraint alert_type_pk
        unique (type, impact, category)
)
    charset = utf8;

create table invalid_alert_category
(
    id       tinyint      not null
        primary key,
    category varchar(255) not null
);

create table project
(
    id         int auto_increment
        primary key,
    name       varchar(255) null,
    url        varchar(255) null comment 'repository url as listed on Coverity Scan',
    github_url varchar(255) null,
    branch     varchar(255) null,
    start_date datetime     null,
    end_date   datetime     null,
    constraint unique_stream
        unique (name, branch)
)
    charset = utf8;

create table commit
(
    id                   int auto_increment
        primary key,
    project_id           int           not null,
    sha                  varchar(255)  null,
    author               varchar(4095) null,
    author_email         varchar(4095) null,
    author_date          datetime      null,
    committer            varchar(4095) null,
    committer_email      varchar(4095) null,
    commit_date          datetime      null,
    message              longtext      null,
    affected_files_count int           null,
    net_lines_added      int           null,
    net_lines_removed    int           null,
    is_merged            varchar(255)  null,
    constraint commit_pk
        unique (sha, project_id),
    constraint sha
        unique (sha),
    constraint commit_project_id_fk
        foreign key (project_id) references project (id)
            on update cascade
)
    charset = utf8;

create table file
(
    id                   int auto_increment
        primary key,
    project_id           int          not null,
    filepath_on_coverity varchar(512) null comment 'begins with /',
    is_processed         tinyint      null,
    constraint file_pk
        unique (project_id, filepath_on_coverity),
    constraint file_project_id_fk
        foreign key (project_id) references project (id)
            on update cascade
)
    charset = utf8;

create table alert
(
    id                  int auto_increment
        primary key,
    cid                 int           not null,
    project_id          int           not null,
    alert_type_id       int           not null,
    status              varchar(255)  null,
    first_detected      date          null,
    owner               varchar(1023) null,
    classification      varchar(1023) null,
    severity            varchar(1023) null,
    action              longtext      null,
    component           longtext      null,
    file_id             int           null,
    function            longtext      null,
    checker             longtext      null,
    count               int           null,
    CWE                 int           null,
    ext_ref             longtext      null,
    first_snapshot_id   int           null,
    function_merge_name longtext      null,
    issue_kind          varchar(255)  null,
    language            varchar(255)  null,
    last_snapshot_id    int           null,
    last_triaged        datetime      null,
    legacy              varchar(255)  null,
    merge_extra         longtext      null,
    merge_key           longtext      null,
    owner_name          varchar(1023) null,
    is_invalid          tinyint       null,
    constraint alert_pk
        unique (cid, project_id),
    constraint alert_alert_type_id_fk
        foreign key (alert_type_id) references alert_type (id)
            on update cascade,
    constraint alert_file_id_fk
        foreign key (file_id) references file (id),
    constraint alert_invalid_alert_category_id_fk
        foreign key (is_invalid) references invalid_alert_category (id)
            on update cascade,
    constraint alert_project_id_fk
        foreign key (project_id) references project (id)
            on update cascade
)
    charset = utf8;

create table actionability
(
    alert_id                 int         not null
        primary key,
    actionability            int         null,
    marked_bug               varchar(45) null,
    file_activity_around_fix varchar(45) null,
    single_fix_commit        int         null,
    fix_commits              longtext    null,
    file_deleted             varchar(45) null,
    delete_commit            int         null,
    file_renamed             varchar(45) null,
    rename_commit            int         null,
    transfered_alert_id      longtext    null,
    suppression              varchar(45) null,
    suppress_commit          int         null,
    suppress_keyword         varchar(45) null,
    constraint actionability_alert_id_fk
        foreign key (alert_id) references alert (id)
            on update cascade,
    constraint actionability_commit_id_fk
        foreign key (single_fix_commit) references commit (id)
            on update cascade
);

create table filecommit
(
    id            int auto_increment
        primary key,
    file_id       int          null,
    commit_id     int          null,
    change_type   varchar(255) null comment 'how the file is changed',
    lines_added   int          null,
    lines_removed int          null,
    constraint filecommit_commit_id_fk
        foreign key (commit_id) references commit (id)
            on update cascade,
    constraint filecommit_file_id_fk
        foreign key (file_id) references file (id)
            on update cascade
)
    comment 'this table keep track of unique file and commit pairs for ease of analysis' charset = utf8;

create table diff
(
    id             int auto_increment
        primary key,
    filecommit_id  int      not null,
    old_start_line int      null,
    old_count      int      null,
    new_start_line int      null,
    new_count      int      null,
    content        longtext null,
    constraint diff_filecommits_idfilecommits_fk
        foreign key (filecommit_id) references filecommit (id)
            on update cascade
)
    charset = utf8;

create table fix_complexity
(
    alert_id              int   not null
        primary key,
    commit_id             int   not null,
    file_count            float null,
    net_loc_change        float null,
    infile_loc_change     float null,
    net_logical_change    float null,
    infile_logical_change float null,
    total_fixed_alerts    int   null,
    infile_fixed_alerts   int   null,
    constraint fix_complexity_alerts_idalerts_fk
        foreign key (alert_id) references alert (id)
            on update cascade,
    constraint fix_complexity_commits_idcommits_fk
        foreign key (commit_id) references commit (id)
            on update cascade
);

create index fix_complexity_commit_id_index
    on fix_complexity (commit_id);

create table merge_date
(
    commit_id  int      not null
        primary key,
    merge_date datetime null,
    constraint merge_date_commits_idcommits_fk
        foreign key (commit_id) references commit (id)
            on update cascade
);

create table occurrence
(
    alert_id       int           not null,
    cid            int           not null,
    event_id       int           not null,
    short_filename varchar(4095) not null,
    file_id        int           null,
    line_number    int           null,
    is_defect_line tinyint       null,
    primary key (alert_id, event_id),
    constraint occurrence_alert_id_fk
        foreign key (alert_id) references alert (id)
            on update cascade
)
    charset = utf8;

create table snapshot
(
    id                     int      not null,
    project_id             int      not null,
    date                   datetime null,
    description            longtext null,
    total_detected         int      null,
    newly_detected         int      null,
    newly_eliminated       int      null,
    analysis_time          time     null,
    lines_of_code          int      null,
    code_version_date      datetime null,
    file_count             int      null,
    function_count         int      null,
    version                longtext null,
    blank_lines            int      null,
    build_time             time     null,
    comment_lines          int      null,
    has_analysis_summaries longtext null,
    target                 longtext null,
    last_snapshot          int      null comment 'keeping track of last snapshot within our data for this stream',
    primary key (id, project_id),
    constraint snapshot_project_id_fk
        foreign key (project_id) references project (id)
            on update cascade
)
    charset = utf8;

