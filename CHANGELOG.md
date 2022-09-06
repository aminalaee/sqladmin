# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Version 0.5.0 - 2022-09-06

### Added

* Add `remote_ajax_refs` in https://github.com/aminalaee/sqladmin/pull/292

### Internal

* Avoid select query with ajax_form_refs in https://github.com/aminalaee/sqladmin/pull/300
* Add docs for form_ajax_refs in https://github.com/aminalaee/sqladmin/pull/302

**Full Changelog**: https://github.com/aminalaee/sqladmin/compare/0.4.0...0.5.0

## Version 0.4.0 - 2022-08-31

### Added

* Add Date and DateTime pickers using Fatpickr in https://github.com/aminalaee/sqladmin/pull/288
* Add Time picker using Flatpickr in https://github.com/aminalaee/sqladmin/pull/294

### Internal
* Remove MomentJS in https://github.com/aminalaee/sqladmin/pull/289
* Remove Select2 widgets in https://github.com/aminalaee/sqladmin/pull/293

**Full Changelog**: https://github.com/aminalaee/sqladmin/compare/0.3.0...0.4.0

## Version 0.3.0 - 2022-08-26

### Added

* Add `AuthenticationBackend` in [#277](https://github.com/aminalaee/sqladmin/pull/277)
* Update Authentication docs in [#278](https://github.com/aminalaee/sqladmin/pull/278)

**Full Changelog**: https://github.com/aminalaee/sqladmin/compare/0.2.1...0.3.0

## Version 0.2.1 - 2022-08-04

### Fixed

* Fix `middlewares` and `ENGINE_TYPE` types in [#266](https://github.com/aminalaee/sqladmin/pull/266)
* Fix middlewares not being applied in [#267](https://github.com/aminalaee/sqladmin/pull/267) and [#271](https://github.com/aminalaee/sqladmin/pull/271)

**Full Changelog**: https://github.com/aminalaee/sqladmin/compare/0.2.0...0.2.1

## Version 0.2.0 - 2022-08-01

### Added

* Add `list_query`, `count_query` and `search_query` options in https://github.com/aminalaee/sqladmin/pull/243
* Add `BaseView` for custom pages in https://github.com/aminalaee/sqladmin/pull/244
* Add `expose` for BaseView in https://github.com/aminalaee/sqladmin/pull/251
* Rename `ModelAdmin` to `ModelView` in https://github.com/aminalaee/sqladmin/pull/249

**Full Changelog**: https://github.com/aminalaee/sqladmin/compare/0.1.12...0.2.0

## Version 0.1.12 - 2022-07-13

### Added

* Add time field converter by @ischaojie in https://github.com/aminalaee/sqladmin/pull/214
* Add Edit button for "Details" page by @cuamckuu in https://github.com/aminalaee/sqladmin/pull/222
* Add column_type_formatters by @aminalaee in https://github.com/aminalaee/sqladmin/pull/239

### Fixed

* Fix lazy subuqery in list query by @aminalaee in https://github.com/aminalaee/sqladmin/pull/212
* Fix missing browser tab title by @cuamckuu in https://github.com/aminalaee/sqladmin/pull/229
* Remove sourceMappingURL in JS files by @aminalaee in https://github.com/aminalaee/sqladmin/pull/231

### New Contributors
* @ischaojie made their first contribution in https://github.com/aminalaee/sqladmin/pull/214
* @cuamckuu made their first contribution in https://github.com/aminalaee/sqladmin/pull/222

**Full Changelog**: https://github.com/aminalaee/sqladmin/compare/0.1.11...0.1.12

## Version 0.1.11 - 2022-06-23

### Added

* Add `form_include_pk` option by @aminalaee in https://github.com/aminalaee/sqladmin/pull/207

### Fixed

* Fix handling of iterable fields by @okapies in https://github.com/aminalaee/sqladmin/pull/204
* Fix nullable Enum form by @aminalaee in https://github.com/aminalaee/sqladmin/pull/205

**Full Changelog**: https://github.com/aminalaee/sqladmin/compare/0.1.10...0.1.11

## Version 0.1.10 - 2022-06-21

### Added

* Add support for one-to-one relationship by @okapies in https://github.com/aminalaee/sqladmin/pull/182
* Add support for UUIDType from sqlalchemy_utils by @okapies in https://github.com/aminalaee/sqladmin/pull/183
* Add sqlalchemy_utils URL, Currency and  Timezone by @aminalaee in https://github.com/aminalaee/sqladmin/pull/185
* Add form_widget_args by @aminalaee in https://github.com/aminalaee/sqladmin/pull/188
* Add column_default_sort by @aminalaee in https://github.com/aminalaee/sqladmin/pull/191

### Fixed

* Fix link relationship to details page when null by @aminalaee in https://github.com/aminalaee/sqladmin/pull/174
* docs: fix typos by @pgrimaud in https://github.com/aminalaee/sqladmin/pull/161
* Allow QuerySelectField override object_list with form_args by @aminalaee in https://github.com/aminalaee/sqladmin/pull/171
* Fix form fields order when specifying columns by @okapies in https://github.com/aminalaee/sqladmin/pull/184
* Fix ModelConverter when `impl` is not callable by @aminalaee in https://github.com/aminalaee/sqladmin/pull/186

### New Contributors
* @pgrimaud made their first contribution in https://github.com/aminalaee/sqladmin/pull/161
* @okapies made their first contribution in https://github.com/aminalaee/sqladmin/pull/183

**Full Changelog**: https://github.com/aminalaee/sqladmin/compare/0.1.9...0.1.10

## Version 0.1.9 - 2022-05-27

### Added

* Add column_formatters by @skarrok in https://github.com/aminalaee/sqladmin/pull/140
* Add column_formatters_detail by @aminalaee in https://github.com/aminalaee/sqladmin/pull/141
* Handling for sqlalchemy_utils EmailType and IPAddressType by @colin99d in https://github.com/aminalaee/sqladmin/pull/150
* Link relationships to detail page by @aminalaee in https://github.com/aminalaee/sqladmin/pull/153

### Fixed

* Function signature typing, and renames by @dwreeves in https://github.com/aminalaee/sqladmin/pull/116
* Fix SQLModel UUID type by @aminalaee in https://github.com/aminalaee/sqladmin/pull/158

### New Contributors
* @skarrok made their first contribution in https://github.com/aminalaee/sqladmin/pull/140
* @colin99d made their first contribution in https://github.com/aminalaee/sqladmin/pull/150

**Full Changelog**: https://github.com/aminalaee/sqladmin/compare/0.1.8...0.1.9

## Version 0.1.8 - 2022-04-19

### Added

* Add csv export support by @dwreeves in https://github.com/aminalaee/sqladmin/pull/101
* Expose Starlette middlewares and debug to the Admin by @tr11 in https://github.com/aminalaee/sqladmin/pull/114

### Fixed

* Fix Export unlimited rows by @aminalaee in https://github.com/aminalaee/sqladmin/pull/107
* Add form and export options docs by @aminalaee in https://github.com/aminalaee/sqladmin/pull/110
* fix docstring issues by adding an explicit handler by @dwreeves in https://github.com/aminalaee/sqladmin/pull/106
* Fix get_model_attr with column labels by @aminalaee in https://github.com/aminalaee/sqladmin/pull/128
* Delay call to `self.get_converter` to use `form_overrides` by @lovetoburnswhen in https://github.com/aminalaee/sqladmin/pull/129

### New Contributors
* @tr11 made their first contribution in https://github.com/aminalaee/sqladmin/pull/114
* @lovetoburnswhen made their first contribution in https://github.com/aminalaee/sqladmin/pull/129

**Full Changelog**: https://github.com/aminalaee/sqladmin/compare/0.1.7...0.1.8

## Version 0.1.7 - 2022-03-22

### Added

* Add SQLModel support by @aminalaee in https://github.com/aminalaee/sqladmin/pull/94
* Add form-specific functionality to ModelAdmin by @dwreeves in https://github.com/aminalaee/sqladmin/pull/97
* Add `UUID` field converter by @aminalaee in https://github.com/aminalaee/sqladmin/pull/82
* Add PostgreSQL `INET` and `MACADDR` converters by @aminalaee in https://github.com/aminalaee/sqladmin/pull/83

### Fixed

* Fix Boolean field checkbox UI by @aminalaee in https://github.com/aminalaee/sqladmin/pull/88
* Fix PostgreSQL UUID PrimaryKey by @aminalaee in https://github.com/aminalaee/sqladmin/pull/92
* Fix Source Code Link by @baurt in https://github.com/aminalaee/sqladmin/pull/95

### New Contributors
* @baurt made their first contribution in https://github.com/aminalaee/sqladmin/pull/95
* @dwreeves made their first contribution in https://github.com/aminalaee/sqladmin/pull/97

**Full Changelog**: https://github.com/aminalaee/sqladmin/compare/0.1.6...0.1.7

## Version 0.1.6 - 2022-03-09

### Added

* FontAwesome6 icons in https://github.com/aminalaee/sqladmin/pull/78
* Add `column_sortable_list` in https://github.com/aminalaee/sqladmin/pull/65
* Add JSON column converters in https://github.com/aminalaee/sqladmin/pull/74

### Fixed

* Fix URL search regex in https://github.com/aminalaee/sqladmin/pull/67
* Fix Enum in Edit page in https://github.com/aminalaee/sqladmin/pull/71

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
