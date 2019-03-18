SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0;
SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0;
SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='TRADITIONAL,ALLOW_INVALID_DATES';
SET @OLD_TIME_ZONE=@@session.time_zone;

DROP SCHEMA IF EXISTS `890coverity` ;
CREATE SCHEMA IF NOT EXISTS `890coverity` DEFAULT CHARACTER SET utf8 ;
USE `890coverity` ;

CREATE TABLE `projects` (
  `idprojects` INT NOT NULL AUTO_INCREMENT,
  `stream` VARCHAR(45) NULL,
  `repository_url` VARCHAR(45) NULL,
  `github_url` VARCHAR(45) NULL,
  `start_date` DATETIME NULL,
  `end_date` DATETIME NULL,
  PRIMARY KEY (`idprojects`));

  CREATE TABLE `snapshots` (
  `idsnapshots` INT NOT NULL,
  `stream` VARCHAR(45) NOT NULL,
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
  `prooject_version` VARCHAR(45) NULL,
  PRIMARY KEY (`idsnapshots`));

CREATE TABLE `bug_types` (
  `idbug_types` INT NOT NULL AUTO_INCREMENT,
  `type` VARCHAR(255) NULL,
  `impact` VARCHAR(45) NULL,
  `category` VARCHAR(255) NULL,
  PRIMARY KEY (`idbug_types`));

CREATE TABLE `files` (
  `idfiles` INT NOT NULL AUTO_INCREMENT,
  `stream` VARCHAR(45) NULL,
  `filepath_on_coverity` VARCHAR(45) NULL,
  `filepath_github` VARCHAR(45) NULL,
  PRIMARY KEY (`idfiles`));

CREATE TABLE `alerts` (
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
  `after_second_snapshot` TINYINT NULL,
  `is_invalid` TINYINT NULL,
  PRIMARY KEY (`cid`, `stream`));


