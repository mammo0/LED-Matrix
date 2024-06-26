% from led_matrix.config.types import ColorTemp
% from led_matrix.server.http_server import SettingsTabs

% setdefault('page_title', 'Settings')
% setdefault("animation_controllers", {})

% rebase("base.tpl", page_title=page_title)


<div class="row">
    <div class="col">
        <ul class="nav nav-tabs" role="tablist">
            % for tab in SettingsTabs:
                <li class="nav-item d-none d-sm-inline" id="nav_{{tab.name.lower()}}">
                    <a class="nav-link {{"active" if active_tab == tab else ""}}" id="tab_{{tab.name.lower()}}" data-toggle="tab" href="#tab_pane_{{tab.name.lower()}}" role="tab" aria-controls="tab_pane_{{tab.name.lower()}}">
                        {{tab.value}}
                    </a>
                </li>
            % end
            <li class="nav-item dropdown d-inline d-sm-none" id="nav_drop">
                <a class="nav-link dropdown-toggle border rounded-top" style="border-bottom-color: white !important;" id="tab_drop" data-toggle="dropdown" href="#" aria-haspopup="true" aria-expanded="false">{{active_tab.value}}</a>
                <div class="dropdown-menu" aria-labelledby="tab_drop">
                    % for tab in SettingsTabs:
                        <a class="dropdown-item {{"d-none" if tab == active_tab else ""}}" id="tab_{{tab.name.lower()}}_dropdown_item" href="#">
                            {{tab.value}}
                        </a>
                    % end
                </div>
            </li>
        </ul>
        <div class="tab-content">
            <div class="tab-pane {{"active" if active_tab == SettingsTabs.MAIN else ""}}" id="tab_pane_main" role="tabpanel" aria-labelledby="tab_main">
                <div class="card border-0">
                    <div class="card-body border-left border-right">
                        <form id="main_settings_form" method="post" action="/settings/{{SettingsTabs.MAIN.name.lower()}}" autocomplete="off">
                            <label for="setting_day">Daytime</label>
                            <ul id="setting_day" class="list-group">
                                % include("settings/day_night.tpl", type="day")
                            </ul>
                            <div class="form-group">
                                <div class="form-check">
                                    <input class="form-check-input" type="checkbox" id="setting_night_brightness_enabled" name="setting_night_brightness_enabled_value" {{"checked" if config.main.night_brightness != -1 else ""}}>
                                    <label class="form-check-label" for="setting_night_brightness_enabled">
                                        Nighttime
                                    </label>
                                </div>
                                <ul id="setting_night" class="list-group {{'d-none' if config.main.night_brightness == -1 else ''}}">
                                    % include("settings/day_night.tpl", type="night")
                                </ul>
                            </div>

                            <div class="form-group">
                                <label for="setting_services_container">Services</label>
                                <div id="setting_services_container">
                                    <div class="form-check">
                                        <input id="setting_tpm2net_toggle" class="form-check-input" type="checkbox" name="enable_tpm2net" {{"checked" if config.main.tpm2net_server else ""}}>
                                        <label class="form-check-label" for="setting_tpm2net_toggle">
                                            TPM2Net Server
                                        </label>
                                    </div>
                                </div>
                            </div>
                        </form>
                    </div>
                    <div class="card-footer border rounded-bottom">
                        <button type="submit" class="btn btn-primary float-right ml-3" form="main_settings_form">Save</button>
                        <a class="btn btn-danger float-right" href="/settings/reset/{{SettingsTabs.MAIN.name.lower()}}">Reset</a>
                    </div>
                </div>
            </div>
            <div class="tab-pane {{"active" if active_tab == SettingsTabs.DEFAULT_ANIMATION else ""}}" id="tab_pane_default_animation" role="tabpanel" aria-labelledby="tab_default_animation">
                <div class="card border-0">
                    <div class="card-body border-left border-right">
                        <%
                            include("animation/selector.tpl", animation_controllers=animation_controllers,
                                                              current_animation_name=config.default_animation.animation_name)
                        %>
                    </div>
                    <div class="card-footer border rounded-bottom">
                        <button id="btn_save_default_animation" type="submit" class="btn btn-primary float-right ml-3" formaction="/settings/{{SettingsTabs.DEFAULT_ANIMATION.name.lower()}}" onclick="submit_animation_form(this.formAction);">Save</button>
                        <a class="btn btn-danger float-right" href="/settings/reset/{{SettingsTabs.DEFAULT_ANIMATION.name.lower()}}">Reset</a>
                    </div>
                </div>
            </div>
            <div class="tab-pane {{"active" if active_tab == SettingsTabs.VARIANT_UPLOAD else ""}}" id="tab_pane_variant_upload" role="tabpanel" aria-labelledby="tab_variant_upload">
                <div class="card border-0">
                    <div class="card-body border-left border-right border-bottom rounded-bottom">
                        <%
                            include("settings/variant_upload.tpl", animation_controllers=animation_controllers)
                        %>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>

<script src="/js/slider.js"></script>
<script src="/js/post_request.js"></script>
<script src="/js/animation_form.js"></script>
<script>
    function preview_brightness(brightness){
        // create a dynamic form object, that contains only the new brightness value
        let form_data = new FormData();
        form_data.append("preview_brightness_value", brightness);

        // send the request
        post_request("/settings/preview_brightness", form_data);
    }

    function preview_color_temp(color_temp){
        // create a dynamic form object, that contains only the new color temperature value
        let form_data = new FormData();
        form_data.append("preview_color_temp_value", color_temp);

        // send the request
        post_request("/settings/preview_color_temp", form_data);
    }

    window.addEventListener("load", function(){
        // toggle night brightness slider visibiltiy with checkbox
        setting_night_brightness_enabled.onchange = function() {
            if(this.checked)
                setting_night.classList.remove("d-none");
            else
                setting_night.classList.add("d-none");
        }

        // keep the dropdown tab selection in sync with the real tabs
        var previos_selected_tab = "{{active_tab.name.lower()}}";
        let tab_items = {
            {{!",".join(["'%s': '%s'" % (tab.name.lower(), tab.value) for tab in SettingsTabs])}}
        };
        function update_tab_environment(selected_dropdown_item, new_tab){
            // hide the selected item
            selected_dropdown_item.classList.add("d-none");

            // show the previous hidden item again
            document.getElementById("tab_" + previos_selected_tab + "_dropdown_item").classList.remove("d-none");

            // update environment
            tab_drop.textContent = tab_items[new_tab];
            previos_selected_tab = new_tab;

            // change the browser address bar to the current selected settings tab
            // so on page reload the same tab is displayed
            window.history.replaceState("", "{{page_title}}", "/settings/" + new_tab);
        }
        for(let tab_name in tab_items){
            let tab_element = document.getElementById("tab_" + tab_name);
            let tab_dropdown_element = document.getElementById("tab_" + tab_name + "_dropdown_item");

            tab_element.onclick = function(){
                update_tab_environment(tab_dropdown_element, tab_name);
            }
            tab_dropdown_element.onclick = function(){
                update_tab_environment(this, tab_name);

                // show the tab
                tab_element.Tab.show();
            }
        }
    });
</script>
