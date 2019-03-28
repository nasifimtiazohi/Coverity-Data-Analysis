SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0;
SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0;
SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='TRADITIONAL,ALLOW_INVALID_DATES';
SET @OLD_TIME_ZONE=@@session.time_zone;

DROP SCHEMA IF EXISTS `890coverity` ;
CREATE SCHEMA IF NOT EXISTS `890coverity` DEFAULT CHARACTER SET utf8;
USE `890coverity` ;

CREATE TABLE `projects` (
  `idprojects` INT NOT NULL AUTO_INCREMENT,
  `project` VARCHAR(45) NULL,
  `repository_url` VARCHAR(255) NULL COMMENT "repository url as listed on Coverity Scan",
  `github_url` VARCHAR(255) NULL,
  `start_date` DATETIME NULL,
  `end_date` DATETIME NULL,
  -- what to do if there is more than one branch?
  `branch` VARCHAR(45) NULL,
  UNIQUE INDEX `project_UNIQUE` (`project` ASC) VISIBLE,
  PRIMARY KEY (`idprojects`));

CREATE TABLE `snapshots` (
`idsnapshots` INT NOT NULL,
-- find out: how coverity uses the term "stream"
`stream` VARCHAR(45) NOT NULL COMMENT "same as project",
`date` DATETIME NULL,
`description` VARCHAR(255) NULL,
`total_detected` INT NULL,
`newly_detected` INT NULL,
`newly_eliminated` INT NULL,
`analysis_time` TIME NULL,
`lines_of_code` INT NULL,
`code_version_date` DATETIME NULL,
`file_count` INT NULL,
`function_count` INT NULL,
`snapshot_verison` VARCHAR(45) NULL,
`blankLinesCount` INT NULL,
`buildTime` TIME NULL,
`commentLinesCount` INT NULL,
`hasAnalysisSummaries` VARCHAR(255) NULL,
`target` VARCHAR(255) NULL,
`last_snapshot` INT COMMENT "keeping track of last snapshot within our data for this stream",
PRIMARY KEY (`idsnapshots`));



CREATE TABLE `bug_types` (
`idbug_types` INT NOT NULL AUTO_INCREMENT,
`type` VARCHAR(255) NULL,
`impact` VARCHAR(45) NULL,
`category` VARCHAR(255) NULL,
PRIMARY KEY (`idbug_types`));

CREATE TABLE `files` (
`idfiles` INT NOT NULL AUTO_INCREMENT,
`project` VARCHAR(45) NULL,
`filepath_on_coverity` VARCHAR(255) NULL COMMENT "begins with /",
PRIMARY KEY (`idfiles`));

CREATE TABLE `filecommits` (
`idfilecommits` INT NOT NULL AUTO_INCREMENT,
`file_id` INT NULL,
`commit_id` INT NULL,
PRIMARY KEY (`idfilecommits`))
COMMENT="this table keep track of unique file and commit pairs for ease of analysis";

CREATE TABLE `890coverity`.`commits` (
  -- I expect more info to come here. e.g. parent?
  `idcommits` INT NOT NULL AUTO_INCREMENT,
  `sha` VARCHAR(255) NULL UNIQUE,
  `author` VARCHAR(255) NULL,
  `author_email` VARCHAR(255) NULL,
  `author_date` DATETIME NULL,
  `committer` VARCHAR(255) NULL,
  `committer_email` VARCHAR(255) NULL,
  `commit_date` DATETIME NULL,
  `message` LONGTEXT NULL,
  `project` VARCHAR(45) NOT NULL,
  PRIMARY KEY (`idcommits`));

CREATE TABLE `890coverity`.`diffs` (
  `iddiffs` INT NOT NULL AUTO_INCREMENT,
  `filecommit_id` INT NOT NULL,
  `old_start_line` INT NULL,
  `old_count` INT NULL,
  `new_start_line` INT NULL,
  `new_count` INT NULL,
  `content` LONGTEXT NULL,
  PRIMARY KEY (`iddiffs`));

CREATE TABLE `alerts` (
`idalerts` INT NOT NULL AUTO_INCREMENT,
`cid` INT NOT NULL,
`stream` VARCHAR(255) NOT NULL,
`bug_type` VARCHAR(255) NULL,
`status` VARCHAR(45) NULL,
`first_detected` DATE NULL,
`owner` VARCHAR(255) NULL,
`classification` VARCHAR(45) NULL,
`severity` VARCHAR(255) NULL,
`action` VARCHAR(255) NULL,
`component` VARCHAR(255) NULL,
`file_id` INT NULL,
`function` VARCHAR(255) NULL,
`checker` VARCHAR(255) NULL,
`count` INT NULL,
`CWE` INT NULL,
`ext_ref` VARCHAR(255) NULL,
`first_snapshot_id` INT NULL,
`function_merge_name` VARCHAR(255) NULL,
`issue_kind` VARCHAR(45) NULL,
`language` VARCHAR(45) NULL,
`last_snapshot_id` INT NULL,
`last_triaged` DATETIME NULL,
`legacy` VARCHAR(45) NULL,
`merge_extra` VARCHAR(255) NULL,
`merge_key` VARCHAR(255) NULL,
`owner_name` VARCHAR(255) NULL,
-- what is the conditions for is_invalid??
`is_invalid` TINYINT NULL,
UNIQUE `unique_index`(`cid`,`stream`),
PRIMARY KEY (`idalerts`));

CREATE TABLE `890coverity`.`occurrences` (
`alert_id` INT NOT NULL,
`cid` INT NOT NULL,
`event_id` INT NOT NULL,
`short_filename` VARCHAR(45) NOT NULL,
`file_id` INT NULL,
`line_number` INT NULL,
PRIMARY KEY (`alert_id`, `event_id`));




