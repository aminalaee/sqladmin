# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Version 0.11.0 - 2023-05-23

### Added

* Add ability to specify custom actions in [#486](https://github.com/aminalaee/sqladmin/pull/486)
* Add `ChoiceType` in [#482](https://github.com/aminalaee/sqladmin/pull/482)
* Add sqlalchemy_fields URLType converter in [#493](https://github.com/aminalaee/sqladmin/pull/493)
* Upgrade fontawesome in [#481](https://github.com/aminalaee/sqladmin/pull/481)

**Full Changelog**: https://github.com/aminalaee/sqladmin/compare/0.10.3...0.11.0

## Version 0.10.3 - 2023-04-21

### Fixed

* Fix ImageType converter in [#471](https://github.com/aminalaee/sqladmin/pull/471)
* reset UploadFile seek after reading in [#473](https://github.com/aminalaee/sqladmin/pull/473)
* Fix unnecessary joins in details and edit page in [#476](https://github.com/aminalaee/sqladmin/pull/476)

## Version 0.10.2 - 2023-04-15

### Fixed

* Fix nullable string fields in [#465](https://github.com/aminalaee/sqladmin/pull/465)
* Fix Multiselect field saving only one value in [#463](https://github.com/aminalaee/sqladmin/pull/463)

## Version 0.10.1 - 2023-03-25

### Fixed

* Fix PK getters for related objects in [#449](https://github.com/aminalaee/sqladmin/pull/449)

## Version 0.10.0 - 2023-03-15

### Breaking change

* Change AuthenticationBackend `authenticate` signature to support OAuth in [#440](https://github.com/aminalaee/sqladmin/pull/440)

### Added

* Add File field in [#424](https://github.com/aminalaee/sqladmin/pull/424)
* Support SQLALchemy Interval type in [#438](https://github.com/aminalaee/sqladmin/pull/438)

### Fixed

* Fix docstrings in [#434](https://github.com/aminalaee/sqladmin/pull/434)
* Update to work with Starlette URL type in url_for in [#444](https://github.com/aminalaee/sqladmin/pull/444)
* Fix nullable Integers to accept zero value in [#445](https://github.com/aminalaee/sqladmin/pull/445)

## Version 0.9.0 - 2023-02-07

### Added

* Support SQLAlchemy v2 in [#411](https://github.com/aminalaee/sqladmin/pull/411)
* Support PostgreSQL arrays in [#414](https://github.com/aminalaee/sqladmin/pull/414)
* Add custom form converters in [#399](https://github.com/aminalaee/sqladmin/pull/399)
* Support SQLAlchemy composite types in [#421](https://github.com/aminalaee/sqladmin/pull/421)
* Add sqlalchemy_utils `PhoneNumberType`, `ColorType` and `ArrowType` in [#422](https://github.com/aminalaee/sqladmin/pull/422)

### Fixed

* Fix re-rendering create/edit page with existing data in [#385](https://github.com/aminalaee/sqladmin/pull/385)
* Fix exclude columns breaking order in [#407](https://github.com/aminalaee/sqladmin/pull/407)
* Fix control relationships in list page in [#409](https://github.com/aminalaee/sqladmin/pull/409)
* Fix asyncpg BigInt query in [#416](https://github.com/aminalaee/sqladmin/pull/416)

## Version 0.8.0 - 2022-11-22

### Added

* Add `save_as` option by @aminalaee in [#377](https://github.com/aminalaee/sqladmin/pull/377)
* Add `save_as_continue` option by @aminalaee in [#379](https://github.com/aminalaee/sqladmin/pull/379)
* Add extra Save buttons for Create/Edit page by @aminalaee in [#373](https://github.com/aminalaee/sqladmin/pull/373)
* Display errors in alert for create/edit page by @aminalaee in [#382](https://github.com/aminalaee/sqladmin/pull/382)

### Fixed

* Fix `_url_for` methods ignoring root_path by @aminalaee in [#371](https://github.com/aminalaee/sqladmin/pull/371)
* Fix export to use `list_query` option by @villqrd in [#381](https://github.com/aminalaee/sqladmin/pull/381)

## Version 0.7.0 - 2022-11-03

### Added

* Add `on_model_change` and `after_model_change` methods in [#342](https://github.com/aminalaee/sqladmin/pull/342)
* Add `on_model_delete` and `after_model_delete` methods in [#343](https://github.com/aminalaee/sqladmin/pull/343)

### Fixed

* Fix search by uuid column in [#366](https://github.com/aminalaee/sqladmin/pull/366)
* Update tests after starlette upgrade in [#344](https://github.com/aminalaee/sqladmin/pull/344)
* Remove hard-coded related model limit in [#354](https://github.com/aminalaee/sqladmin/pull/354)
* Improve items list UI in [#349](https://github.com/aminalaee/sqladmin/pull/349)
* Make navbar work on small screens in [#362](https://github.com/aminalaee/sqladmin/pull/362)

### Internal
* Add mypy check with config no_implicit_optional in [#360](https://github.com/aminalaee/sqladmin/pull/360)
* Support test-suite py311 in [#365](https://github.com/aminalaee/sqladmin/pull/365)
* Add py.typed for the package to ship its typing information in [#346](https://github.com/aminalaee/sqladmin/pull/346)

## Version 0.6.1 - 2022-09-25

### Fixed

* Fix Boolean field for both nullable and non-nullable cases in [#336](https://github.com/aminalaee/sqladmin/pull/336)
* Fix Flatpickr not respecting readonly inputs in [#336](https://github.com/aminalaee/sqladmin/pull/336)
* Disable batch delete when can_delete permission is not provided in [#335](https://github.com/aminalaee/sqladmin/pull/335)

## Version 0.6.0 - 2022-09-19

### Added

* Add bulk delete action in [#317](https://github.com/aminalaee/sqladmin/pull/317)

### Fixed

* Handle null values when column is nullable in [#323](https://github.com/aminalaee/sqladmin/pull/323)
* Switch Boolean field to select field in [#321](https://github.com/aminalaee/sqladmin/pull/321)

### Internal

* Fix form_ajax_refs example in documentation in [#311](https://github.com/aminalaee/sqladmin/pull/311)
* Remove watch in mkdocstrings mkdocs's config in [#306](https://github.com/aminalaee/sqladmin/pull/306)

## Version 0.5.0 - 2022-09-06

### Added

* Add `remote_ajax_refs` in [#292](https://github.com/aminalaee/sqladmin/pull/292)

### Internal

* Avoid select query with ajax_form_refs in [#300](https://github.com/aminalaee/sqladmin/pull/300)
* Add docs for form_ajax_refs in [#302](https://github.com/aminalaee/sqladmin/pull/302)

## Version 0.4.0 - 2022-08-31

## Added

* Add Date and DateTime pickers using Fatpickr in [#288](https://github.com/aminalaee/sqladmin/pull/288)
* Add Time picker using Flatpickr in [#294](https://github.com/aminalaee/sqladmin/pull/294)

## Internal
* Remove MomentJS in [#289](https://github.com/aminalaee/sqladmin/pull/289)
* Remove Select2 widgets in [#293](https://github.com/aminalaee/sqladmin/pull/293)

## Version 0.3.0 - 2022-08-26

### Added

* Add `AuthenticationBackend` in [#277](https://github.com/aminalaee/sqladmin/pull/277)
* Update Authentication docs in [#278](https://github.com/aminalaee/sqladmin/pull/278)

## Version 0.2.1 - 2022-08-04

### Fixed

* Fix `middlewares` and `ENGINE_TYPE` types in [#266](https://github.com/aminalaee/sqladmin/pull/266)
* Fix middlewares not being applied in [#267](https://github.com/aminalaee/sqladmin/pull/267) and [#271](https://github.com/aminalaee/sqladmin/pull/271)

## Version 0.2.0 - 2022-08-01

### Added

* Add `list_query`, `count_query` and `search_query` options in [#243](https://github.com/aminalaee/sqladmin/pull/243)
* Add `BaseView` for custom pages in [#244](https://github.com/aminalaee/sqladmin/pull/244)
* Add `expose` for BaseView in [#251](https://github.com/aminalaee/sqladmin/pull/251)
* Rename `ModelAdmin` to `ModelView` in [#249](https://github.com/aminalaee/sqladmin/pull/249)

## Version 0.1.12 - 2022-07-13

### Added

* Add time field converter in [#214](https://github.com/aminalaee/sqladmin/pull/214)
* Add Edit button for "Details" page in [#222](https://github.com/aminalaee/sqladmin/pull/222)
* Add column_type_formatters in [#239](https://github.com/aminalaee/sqladmin/pull/239)

### Fixed

* Fix lazy subuqery in list query in [#212](https://github.com/aminalaee/sqladmin/pull/212)
* Fix missing browser tab title in [#229](https://github.com/aminalaee/sqladmin/pull/229)
* Remove sourceMappingURL in JS files in [#231](https://github.com/aminalaee/sqladmin/pull/231)

## Version 0.1.11 - 2022-06-23

### Added

* Add `form_include_pk` option in [#207](https://github.com/aminalaee/sqladmin/pull/207)

### Fixed

* Fix handling of iterable fields in [#204](https://github.com/aminalaee/sqladmin/pull/204)
* Fix nullable Enum form in [#205](https://github.com/aminalaee/sqladmin/pull/205)

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

## Version 0.1.6 - 2022-03-09

### Added

* FontAwesome6 icons in [#78](https://github.com/aminalaee/sqladmin/pull/78)
* Add `column_sortable_list` in [#65](https://github.com/aminalaee/sqladmin/pull/65)
* Add JSON column converters in [#74](https://github.com/aminalaee/sqladmin/pull/74)

### Fixed

* Fix URL search regex in [#67](https://github.com/aminalaee/sqladmin/pull/67)
* Fix Enum in Edit page in [#71](https://github.com/aminalaee/sqladmin/pull/71)

## Version 0.1.5 - 2022-02-24

### Added

* Authentication in [#37](https://github.com/aminalaee/sqladmin/pull/37)
* Add Edit view page in [#60](https://github.com/aminalaee/sqladmin/pull/60)
* Add `column_searchable_list` in [#61](https://github.com/aminalaee/sqladmin/pull/61)

### Internal

* Cleanup DB queries in [#51](https://github.com/aminalaee/sqladmin/pull/54)

## Version 0.1.4 - 2022-02-16

### Added

* Allow templates to be configured in [#52](https://github.com/aminalaee/sqladmin/pull/52)
* Add page size option links in [#34](https://github.com/aminalaee/sqladmin/pull/34)

### Fixed

* Improve pagination in [#36](https://github.com/aminalaee/sqladmin/pull/36)

### Internal

* Instantiate ModelAdmin internally to avoid class methods in [#31](https://github.com/aminalaee/sqladmin/pull/31)

## Version 0.1.3 - 2022-01-24

### Added

* Add `title` and `logo` options in [#20](https://github.com/aminalaee/sqladmin/pull/20)
* Adding `order_by` to list pagination query in [#25](https://github.com/aminalaee/sqladmin/pull/25)
* Allow Relationship properties in list and detail views in [#22](https://github.com/aminalaee/sqladmin/pull/22)
