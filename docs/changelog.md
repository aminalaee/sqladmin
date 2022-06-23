# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Version 0.1.11 - 2022-06-23

### Added

* Add `form_include_pk` option in [#207](https://github.com/aminalaee/sqladmin/pull/207)

### Fixed

* Fix handling of iterable fields in [#204](https://github.com/aminalaee/sqladmin/pull/204)
* Fix nullable Enum form in [#205](https://github.com/aminalaee/sqladmin/pull/205)

**Full Changelog**: https://github.com/aminalaee/sqladmin/compare/0.1.10...0.1.11

## Version 0.1.10 - 2022-06-21

### Added

* Add support for one-to-one relationship in [#186](https://github.com/aminalaee/sqladmin/pull/182)
* Add support for UUIDType from sqlalchemy_utils in [#183](https://github.com/aminalaee/sqladmin/pull/183)
* Add sqlalchemy_utils URL, Currency and  Timezone in [#185](https://github.com/aminalaee/sqladmin/pull/185)
* Add form_widget_args in [#188](https://github.com/aminalaee/sqladmin/pull/188)
* Add column_default_sort in [#191](https://github.com/aminalaee/sqladmin/pull/191)

### Fixed

* Fix link relationship to details page when null in [#174](https://github.com/aminalaee/sqladmin/pull/174)
* docs: fix typos in [#161](https://github.com/aminalaee/sqladmin/pull/161)
* Allow QuerySelectField override object_list with form_args in [#171](https://github.com/aminalaee/sqladmin/pull/171)
* Fix form fields order when specifying columns in [#184](https://github.com/aminalaee/sqladmin/pull/184)
* Fix ModelConverter when `impl` is not callable in [#186](https://github.com/aminalaee/sqladmin/pull/186)

## Version 0.1.9 - 2022-05-27

### Added

* Add `column_formatters` in [#140](https://github.com/aminalaee/sqladmin/pull/140)
* Add `column_formatters_detail` in [#141](https://github.com/aminalaee/sqladmin/pull/141)
* Handling for sqlalchemy_utils EmailType and IPAddressType in [#150](https://github.com/aminalaee/sqladmin/pull/150)
* Link relationships to detail page in [#153](https://github.com/aminalaee/sqladmin/pull/153)

### Fixed

* Function signature typing, and renames in [#116](https://github.com/aminalaee/sqladmin/pull/116)
* Fix SQLModel UUID type in [#158](https://github.com/aminalaee/sqladmin/pull/158)

## Version 0.1.8 - 2022-04-19

### Added

* Add csv export support in [#101](https://github.com/aminalaee/sqladmin/pull/101)
* Expose Starlette middlewares and debug to the Admin in [#114](https://github.com/aminalaee/sqladmin/pull/114)

### Fixed

* Fix Export unlimited rows in [#107](https://github.com/aminalaee/sqladmin/pull/107)
* Add form and export options docs in [#110](https://github.com/aminalaee/sqladmin/pull/110)
* fix docstring issues by adding an explicit handler in [#106](https://github.com/aminalaee/sqladmin/pull/106)
* Fix get_model_attr with column labels in [#128](https://github.com/aminalaee/sqladmin/pull/128)
* Delay call to `self.get_converter` to use `form_overrides` in [#129](https://github.com/aminalaee/sqladmin/pull/129)

**Full Changelog**: https://github.com/aminalaee/sqladmin/compare/0.1.7...0.1.8

## Version 0.1.7 - 2022-03-22

### Added

* Add SQLModel support in [#94](https://github.com/aminalaee/sqladmin/pull/94)
* Add form-specific functionality to ModelAdmin in [#97](https://github.com/aminalaee/sqladmin/pull/97)
* Add `UUID` field converter in [#82](https://github.com/aminalaee/sqladmin/pull/82)
* Add PostgreSQL `INET` and `MACADDR` converters in [#83](https://github.com/aminalaee/sqladmin/pull/83)

### Fixed

* Fix Boolean field checkbox UI in [#88](https://github.com/aminalaee/sqladmin/pull/88)
* Fix PostgreSQL UUID PrimaryKey in [#92](https://github.com/aminalaee/sqladmin/pull/92)
* Fix Source Code Link in [#95](https://github.com/aminalaee/sqladmin/pull/95)

**Full Changelog**: https://github.com/aminalaee/sqladmin/compare/0.1.6...0.1.7

## Version 0.1.6 - 2022-03-09

### Added

* FontAwesome6 icons in [#78](https://github.com/aminalaee/sqladmin/pull/78)
* Add `column_sortable_list` in [#65](https://github.com/aminalaee/sqladmin/pull/65)
* Add JSON column converters in [#74](https://github.com/aminalaee/sqladmin/pull/74)

### Fixed

* Fix URL search regex in [#67](https://github.com/aminalaee/sqladmin/pull/67)
* Fix Enum in Edit page in [#71](https://github.com/aminalaee/sqladmin/pull/71)

**Full Changelog**: https://github.com/aminalaee/sqladmin/compare/0.1.5...0.1.6

## Version 0.1.5 - 2022-02-24

### Added

* Authentication in [#37](https://github.com/aminalaee/sqladmin/pull/37)
* Add Edit view page in [#60](https://github.com/aminalaee/sqladmin/pull/60)
* Add `column_searchable_list` in [#61](https://github.com/aminalaee/sqladmin/pull/61)

### Internal

* Cleanup DB queries in [#51](https://github.com/aminalaee/sqladmin/pull/54)

**Full Changelog**: https://github.com/aminalaee/sqladmin/compare/0.1.4...0.1.5

## Version 0.1.4 - 2022-02-16

### Added

* Allow templates to be configured in [#52](https://github.com/aminalaee/sqladmin/pull/52)
* Add page size option links in [#34](https://github.com/aminalaee/sqladmin/pull/34)

### Fixed

* Improve pagination in [#36](https://github.com/aminalaee/sqladmin/pull/36)

### Internal

* Instantiate ModelAdmin internally to avoid class methods in [#31](https://github.com/aminalaee/sqladmin/pull/31)

**Full Changelog**: https://github.com/aminalaee/sqladmin/compare/0.1.3...0.1.4

## Version 0.1.3 - 2022-01-24

### Added

* Add `title` and `logo` options in [#20](https://github.com/aminalaee/sqladmin/pull/20)
* Adding `order_by` to list pagination query in [#25](https://github.com/aminalaee/sqladmin/pull/25)
* Allow Relationship properties in list and detail views in [#22](https://github.com/aminalaee/sqladmin/pull/22)

**Full Changelog**: https://github.com/aminalaee/sqladmin/compare/0.1.2...0.1.3
