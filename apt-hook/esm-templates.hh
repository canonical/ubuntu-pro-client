#include <string>
#include <vector>

#define MOTD_ESM_SERVICE_STATUS_MESSAGE_STATIC_PATH      "/var/lib/ubuntu-advantage/messages/motd-esm-service-status"
#define MOTD_APPS_NO_PKGS_TEMPLATE_PATH                  "/var/lib/ubuntu-advantage/messages/motd-no-packages-apps.tmpl"
#define MOTD_INFRA_NO_PKGS_TEMPLATE_PATH                 "/var/lib/ubuntu-advantage/messages/motd-no-packages-infra.tmpl"
#define MOTD_APPS_PKGS_TEMPLATE_PATH                     "/var/lib/ubuntu-advantage/messages/motd-packages-apps.tmpl"
#define MOTD_INFRA_PKGS_TEMPLATE_PATH                    "/var/lib/ubuntu-advantage/messages/motd-packages-infra.tmpl"
#define MOTD_APPS_PKGS_STATIC_PATH                       "/var/lib/ubuntu-advantage/messages/motd-packages-apps"
#define MOTD_INFRA_PKGS_STATIC_PATH                      "/var/lib/ubuntu-advantage/messages/motd-packages-infra"
#define APT_PRE_INVOKE_APPS_NO_PKGS_TEMPLATE_PATH        "/var/lib/ubuntu-advantage/messages/apt-pre-invoke-no-packages-apps.tmpl"
#define APT_PRE_INVOKE_INFRA_NO_PKGS_TEMPLATE_PATH       "/var/lib/ubuntu-advantage/messages/apt-pre-invoke-no-packages-infra.tmpl"
#define APT_PRE_INVOKE_APPS_PKGS_TEMPLATE_PATH           "/var/lib/ubuntu-advantage/messages/apt-pre-invoke-packages-apps.tmpl"
#define APT_PRE_INVOKE_APPS_PKGS_STATIC_PATH             "/var/lib/ubuntu-advantage/messages/apt-pre-invoke-packages-apps"
#define APT_PRE_INVOKE_INFRA_PKGS_TEMPLATE_PATH          "/var/lib/ubuntu-advantage/messages/apt-pre-invoke-packages-infra.tmpl"
#define APT_PRE_INVOKE_INFRA_PKGS_STATIC_PATH            "/var/lib/ubuntu-advantage/messages/apt-pre-invoke-packages-infra"
#define APT_PRE_INVOKE_MESSAGE_STATIC_PATH               "/var/lib/ubuntu-advantage/messages/apt-pre-invoke-esm-service-status"

#define ESM_APPS_PKGS_COUNT_TEMPLATE_VAR "{ESM_APPS_PKG_COUNT}"
#define ESM_APPS_PACKAGES_TEMPLATE_VAR "{ESM_APPS_PACKAGES}"
#define ESM_INFRA_PKGS_COUNT_TEMPLATE_VAR "{ESM_INFRA_PKG_COUNT}"
#define ESM_INFRA_PACKAGES_TEMPLATE_VAR "{ESM_INFRA_PACKAGES}"

void process_all_templates();
