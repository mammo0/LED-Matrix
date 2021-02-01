% from common.config import Config
% from server.http_server import SettingsTabs

% setdefault('page_title', 'Settings')
% setdefault("animations", {})
% setdefault("default_animation_name", "")

% rebase("base.tpl", page_title=page_title)


<div class="row">
    <div class="col">
        <ul class="nav nav-tabs" role="tablist">
            % for tab in SettingsTabs:
                <li class="nav-item d-none d-sm-inline" id="nav_{{tab.name}}">
                    <a class="nav-link {{"active" if active_tab == tab else ""}}" id="tab_{{tab.name}}" data-toggle="tab" href="#tab_pane_{{tab.name}}" role="tab" aria-controls="tab_pane_{{tab.name}}">
                        {{tab.value}}
                    </a>
                </li>
            % end
            <li class="nav-item dropdown d-inline d-sm-none" id="nav_drop">
                <a class="nav-link dropdown-toggle border rounded-top" style="border-bottom-color: white !important;" id="tab_drop" data-toggle="dropdown" href="#" aria-haspopup="true" aria-expanded="false">{{active_tab.value}}</a>
                <div class="dropdown-menu" aria-labelledby="tab_drop">
                    % for tab in SettingsTabs:
                        <a class="dropdown-item {{"d-none" if tab == active_tab else ""}}" id="tab_drop_{{tab.name}}" href="#">
                            {{tab.value}}
                        </a>
                    % end
                </div>
            </li>
        </ul>
        <div class="tab-content">
            <div class="tab-pane {{"active" if active_tab == SettingsTabs.main else ""}}" id="tab_pane_main" role="tabpanel" aria-labelledby="tab_main">
                <div class="card border-0">
                    <div class="card-body border-left border-right">
                        <form id="main_settings_form" method="post" action="/settings/{{SettingsTabs.main.name}}" autocomplete="off">
                            <div class="form-group">
                                <label for="setting_brightness_container">Brightness</label>
                                <div id="setting_brightness_container" class="slider_container d-flex align-items-center">
                                    <input id="setting_brightness_slider"
                                           class="custom-range slider flex-grow-1 mr-2"
                                           style="width:1px"
                                           name="brightness_value"
                                           type="range"
                                           min="0" max="100" value="{{current_brightness}}">
                                    <span class="pr-2">
                                        <span class="slider-value badge badge-warning" style="font-size:3ex;width:3em"></span>
                                    </span>
                                    <a id="setting_brightness_preview_btn" class="btn btn-success">Preview</a>
                                </div>
                            </div>

                            <div class="form-group">
                                <label for="setting_services_container">Services</label>
                                <div id="setting_services_container">
                                    <div class="form-check">
                                        <input id="setting_rest_toggle" class="form-check-input" type="checkbox" name="enable_rest" {{"checked" if config.get(Config.MAIN.RestServer) else ""}}>
                                        <label class="form-check-label" for="setting_rest_toggle">
                                            REST Server
                                        </label>
                                    </div>
                                    <div class="form-check">
                                        <input id="setting_tpm2net_toggle" class="form-check-input" type="checkbox" name="enable_tpm2net" {{"checked" if config.get(Config.MAIN.TPM2NetServer) else ""}}>
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
                        <a class="btn btn-danger float-right" href="/settings/reset/{{SettingsTabs.main.name}}">Reset</a>
                    </div>
                </div>
            </div>
            <div class="tab-pane {{"active" if active_tab == SettingsTabs.default_animation else ""}}" id="tab_pane_default_animation" role="tabpanel" aria-labelledby="tab_default_animation">
                <div class="card border-0">
                    <div class="card-body border-left border-right">
                        <%
                            include("animation/selector.tpl", animations=animations,
                                                              current_animation_name=default_animation_name)
                        %>
                    </div>
                    <div class="card-footer border rounded-bottom">
                        <button id="btn_save_default_animation" type="submit" class="btn btn-primary float-right ml-3">Save</button>
                        <a class="btn btn-danger float-right" href="/settings/reset/{{SettingsTabs.default_animation.name}}">Reset</a>
                    </div>
                </div>
            </div>
            <div class="tab-pane {{"active" if active_tab == SettingsTabs.schedule_table else ""}}" id="tab_pane_schedule_table" role="tabpanel" aria-labelledby="tab_schedule_table">
                <div class="card border-0">
                    <div class="card-body border-left border-right border-bottom rounded-bottom">
                        % include("schedule/table.tpl")
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>

<script src="/js/slider.js"></script>
<script src="/js/post_request.js"></script>
<script>
    window.addEventListener("load", function(){
        setting_brightness_preview_btn.onclick = function(){
            // create a dynamic form object, that contains only the new brightness value
            let form_data = new FormData();
            form_data.append(setting_brightness_slider.name, setting_brightness_slider.value);

            // send the request
            post_request("/settings/preview_brightness", form_data);
        }

        btn_save_default_animation.onclick = function(){
            // this selector and form is defined by 'animation_settings.tpl'
            let animation_selector = document.getElementById("animation_selector");
            let animation_form = document.getElementById("animation_settings_form_" + animation_selector.value);

            // add a hidden field that contains the selected animation name
            const hiddenField = document.createElement('input');
            hiddenField.type = 'hidden';
            hiddenField.name = "selected_animation_name";
            hiddenField.value = animation_selector.value;
            animation_form.appendChild(hiddenField);

            // submit the form
            animation_form.action = "/settings/{{SettingsTabs.default_animation.name}}"
            animation_form.submit();
        }

        // keep the dropdown tab selection in sync with the real tabs
        var previos_selected_tab = "{{active_tab.name}}";
        function update_tab_environment(selected_dropdown_item, new_dropdown_content, new_tab){
            // hide the selected item
            selected_dropdown_item.classList.add("d-none");

            // show the previous hidden item again
            document.getElementById("tab_drop_" + previos_selected_tab).classList.remove("d-none");

            // update environment
            tab_drop.innerHTML = new_dropdown_content;
            previos_selected_tab = new_tab;

            // change the browser address bar to the current selected settings tab
            // so on page reload the same tab is displayed
            window.history.replaceState("", "{{page_title}}", "/settings/" + new_tab);
        }
        % for tab in SettingsTabs:
            tab_{{tab.name}}.onclick = function(){
                update_tab_environment(tab_drop_{{tab.name}}, "{{tab.value}}", "{{tab.name}}");
            }
            tab_drop_{{tab.name}}.onclick = function(){
                update_tab_environment(this, "{{tab.value}}", "{{tab.name}}");

                // show the tab
                tab_{{tab.name}}.Tab.show()
            }
        % end
    });
</script>
