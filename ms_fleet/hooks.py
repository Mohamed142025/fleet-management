app_name = "ms_fleet"
app_title = "MS Fleet"
app_publisher = "Mohamed Sayed"
app_description = "Fleet and transport management with a driver PWA"
app_email = "Mohameddbs53@gmail.com"
app_license = "mit"

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "ms_fleet",
# 		"logo": "/assets/ms_fleet/logo.png",
# 		"title": "MS Fleet",
# 		"route": "/ms_fleet",
# 		"has_permission": "ms_fleet.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/ms_fleet/css/ms_fleet.css"
# app_include_js = "/assets/ms_fleet/js/ms_fleet.js"

# include js, css files in header of web template
# web_include_css = "/assets/ms_fleet/css/ms_fleet.css"
# web_include_js = "/assets/ms_fleet/js/ms_fleet.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "ms_fleet/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "ms_fleet/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# automatically load and sync documents of this doctype from downstream apps
# importable_doctypes = [doctype_1]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "ms_fleet.utils.jinja_methods",
# 	"filters": "ms_fleet.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "ms_fleet.install.before_install"
# after_install = "ms_fleet.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "ms_fleet.uninstall.before_uninstall"
# after_uninstall = "ms_fleet.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "ms_fleet.utils.before_app_install"
# after_app_install = "ms_fleet.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "ms_fleet.utils.before_app_uninstall"
# after_app_uninstall = "ms_fleet.utils.after_app_uninstall"

# Build
# ------------------
# To hook into the build process

# after_build = "ms_fleet.build.after_build"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "ms_fleet.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"ms_fleet.tasks.all"
# 	],
# 	"daily": [
# 		"ms_fleet.tasks.daily"
# 	],
# 	"hourly": [
# 		"ms_fleet.tasks.hourly"
# 	],
# 	"weekly": [
# 		"ms_fleet.tasks.weekly"
# 	],
# 	"monthly": [
# 		"ms_fleet.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "ms_fleet.install.before_tests"

# Extend DocType Class
# ------------------------------
#
# Specify custom mixins to extend the standard doctype controller.
# extend_doctype_class = {
# 	"Task": "ms_fleet.custom.task.CustomTaskMixin"
# }

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "ms_fleet.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "ms_fleet.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["ms_fleet.utils.before_request"]
# after_request = ["ms_fleet.utils.after_request"]

# Job Events
# ----------
# before_job = ["ms_fleet.utils.before_job"]
# after_job = ["ms_fleet.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"ms_fleet.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

# Translation
# ------------
# List of apps whose translatable strings should be excluded from this app's translations.
# ignore_translatable_strings_from = []

# ms_fleet: fleet and transport management with a driver PWA (/driver)
# --------------------------------------------------------------------

required_apps = ["erpnext", "hrms"]

after_install = "ms_fleet.setup.after_install"
after_migrate = "ms_fleet.setup.after_migrate"

doctype_js = {
	"Driver": "public/js/driver.js",
}

doc_events = {
	"Purchase Invoice": {
		"on_cancel": "ms_fleet.settlement.release_trips",
		"on_trash": "ms_fleet.settlement.release_trips",
	},
}

scheduler_events = {
	"cron": {
		"*/5 * * * *": ["ms_fleet.tasks.check_response_timeouts"],
	},
	"daily": ["ms_fleet.tasks.expiry_alerts"],
}

# The driver app is a single page under /driver.
website_route_rules = [
	{"from_route": "/driver/<path:app_path>", "to_route": "driver"},
]

# This site can be the push relay behind Frappe's push service (push_relay_server_url).
override_whitelisted_methods = {
	"notification_relay.api.get_config": "ms_fleet.relay.api.get_config",
	"notification_relay.api.auth.get_credential": "ms_fleet.relay.api.get_credential",
	"notification_relay.api.token.add": "ms_fleet.relay.api.add_token",
	"notification_relay.api.token.remove": "ms_fleet.relay.api.remove_token",
	"notification_relay.api.send_notification.user": "ms_fleet.relay.api.send_to_user",
	"notification_relay.api.send_notification.topic": "ms_fleet.relay.api.topics_not_supported",
	"notification_relay.api.topic.add": "ms_fleet.relay.api.topics_not_supported",
	"notification_relay.api.topic.remove": "ms_fleet.relay.api.topics_not_supported",
	"notification_relay.api.topic.subscribe": "ms_fleet.relay.api.topics_not_supported",
	"notification_relay.api.topic.unsubscribe": "ms_fleet.relay.api.topics_not_supported",
}
