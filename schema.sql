SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0;
SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0;
SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='TRADITIONAL,ALLOW_INVALID_DATES';
SET @OLD_TIME_ZONE=@@session.time_zone;

DROP SCHEMA IF EXISTS `890coverity` ;
CREATE SCHEMA IF NOT EXISTS `890coverity` DEFAULT CHARACTER SET utf8;
USE `890coverity` ;

CREATE TABLE `projects` (
  `idprojects` INT NOT NULL AUTO_INCREMENT,
  `name` VARCHAR(255) NULL,
  `repository_url_on_coverity` VARCHAR(255) NULL COMMENT "repository url as listed on Coverity Scan",
  `github_url` VARCHAR(255) NULL,
  `stream_count` INT NOT NULL,
  `branch_aka_stream` VARCHAR(255) NULL,  -- if we find two streams for any project (unlikely) we have to make use of this column
  `start_date` DATETIME NULL,
  `end_date` DATETIME NULL,
  UNIQUE INDEX `unique_stream` (`name`,`branch_aka_stream`),
  PRIMARY KEY (`idprojects`));

CREATE TABLE `snapshots` (
`idsnapshots` INT NOT NULL,
`stream` VARCHAR(255) NOT NULL,
`date` DATETIME NULL,
`description` LONGTEXT NULL,
`total_detected` INT NULL,
`newly_detected` INT NULL,
`newly_eliminated` INT NULL,
`analysis_time` TIME NULL,
`lines_of_code` INT NULL,
`code_version_date` DATETIME NULL,
`file_count` INT NULL,
`function_count` LONGTEXT NULL,
`blankLinesCount` INT NULL,
`buildTime` TIME NULL,
`commentLinesCount` INT NULL,
`hasAnalysisSummaries` LONGTEXT NULL,
`target` LONGTEXT NULL,
`last_snapshot` INT COMMENT "keeping track of last snapshot within our data for this stream",
PRIMARY KEY (`idsnapshots`));



CREATE TABLE `bug_types` (
`idbug_types` INT NOT NULL AUTO_INCREMENT,
`type` VARCHAR(255) NULL,
`impact` VARCHAR(255) NULL,
`category` VARCHAR(255) NULL,
PRIMARY KEY (`idbug_types`));

CREATE TABLE `files` (
  -- how to handle branching? not current concern
`idfiles` INT NOT NULL AUTO_INCREMENT,
`project` VARCHAR(255) NULL,
`filepath_on_coverity` VARCHAR(4095) NULL COMMENT "begins with /",
PRIMARY KEY (`idfiles`));

CREATE TABLE `filecommits` (
`idfilecommits` INT NOT NULL AUTO_INCREMENT,
`file_id` INT NULL,
`commit_id` INT NULL,
`change_type` VARCHAR(255) NULL COMMENT "how the file is changed",
`lines_added` INT NULL,
`lines_removed` INT NULL,
PRIMARY KEY (`idfilecommits`))
COMMENT="this table keep track of unique file and commit pairs for ease of analysis";

CREATE TABLE `890coverity`.`commits` (
  -- I expect more info to come here. e.g. parent?
  `idcommits` INT NOT NULL AUTO_INCREMENT,
  `sha` VARCHAR(4095) NULL UNIQUE,
  `author` VARCHAR(4095) NULL,
  `author_email` VARCHAR(4095) NULL,
  `author_date` DATETIME NULL,
  `committer` VARCHAR(4095) NULL,
  `committer_email` VARCHAR(4095) NULL,
  `commit_date` DATETIME NULL,
  `message` LONGTEXT NULL,
  `affected_files_count` INT NULL,
  `net_lines_added` INT NULL,
  `net_lines_removed` INT NULL, 
  `is_merged` VARCHAR(255),
  `project` VARCHAR(255) NOT NULL,
  PRIMARY KEY (`idcommits`));

CREATE TABLE `890coverity`.`commit_parents` (
  `commit_id` INT NOT NULL,
  `parent_hash` VARCHAR(4095) NULL,
  `parent_commit_id` INT NULL);

CREATE TABLE `890coverity`.`diffs` (
  `iddiffs` INT NOT NULL AUTO_INCREMENT,
  `filecommit_id` INT NOT NULL,
  `old_start_line` INT NULL,
  `old_count` INT NULL,
  `new_start_line` INT NULL,
  `new_count` INT NULL,
  `content` LONGTEXT NULL,
  PRIMARY KEY (`iddiffs`));

CREATE TABLE `890coverity`.`parsed_diff` (
  `diff_id` INT NOT NULL,
  `change_type` VARCHAR(255) NULL,
  `line_number` INT NULL,
  `code` LONGTEXT NULL);

CREATE TABLE `alerts` (
`idalerts` INT NOT NULL AUTO_INCREMENT,
`cid` INT NOT NULL,
`stream` VARCHAR(255) NOT NULL,
`bug_type` VARCHAR(255) NULL,
`status` VARCHAR(255) NULL,
`first_detected` DATE NULL,
`owner` VARCHAR(4095) NULL,
`classification` VARCHAR(4095) NULL,
`severity` VARCHAR(4095) NULL,
`action` LONGTEXT NULL,
`component` VARCHAR(4095) NULL,
`file_id` INT NULL,
`function` VARCHAR(4095) NULL,
`checker` VARCHAR(4095) NULL,
`count` INT NULL,
`CWE` INT NULL,
`ext_ref` LONGTEXT NULL,
`first_snapshot_id` INT NULL,
`function_merge_name` LONGTEXT NULL,
`issue_kind` VARCHAR(255) NULL,
`language` VARCHAR(255) NULL,
`last_snapshot_id` INT NULL,
`last_triaged` DATETIME NULL,
`legacy` VARCHAR(255) NULL,
`merge_extra` LONGTEXT NULL,
`merge_key` LONGTEXT NULL,
`owner_name` VARCHAR(4095) NULL,
-- what is the conditions for is_invalid??
`is_invalid` TINYINT NULL,
UNIQUE `unique_index`(`cid`,`stream`),
PRIMARY KEY (`idalerts`));

CREATE TABLE `890coverity`.`occurrences` (
`alert_id` INT NOT NULL,
`cid` INT NOT NULL,
`event_id` INT NOT NULL,
`short_filename` VARCHAR(4095) NOT NULL,
`file_id` INT NULL,
`line_number` INT NULL,
`is_defect_line` TINYINT,
PRIMARY KEY (`alert_id`, `event_id`));




