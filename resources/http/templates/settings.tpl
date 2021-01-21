% setdefault('page_title', 'Settings')
% rebase("base.tpl", title=page_title)

<h1>
    {{page_title}}
    <hr/>
</h1>

<div class="main_settings row justify-content-center">
    <div class="col">
        <ul class="nav nav-tabs" role="tablist">
            <li class="nav-item">
                <a class="nav-link active" id="tab_main" data-toggle="tab" href="#tab_pane_main" role="tab" aria-controls="tab_pane_main" aria-selected="true">
                    Main
                </a>
            </li>
            <li class="nav-item" role="presentation">
                <a class="nav-link" id="tab_default_animation" data-toggle="tab" href="#tab_pane_default_animation_pane" role="tab" aria-controls="tab_pane_default_animation_pane" aria-selected="true">
                    Default Animation
                </a>
            </li>
        </ul>
        <div class="tab-content">
            <div class="tab-pane show active" id="tab_pane_main" role="tabpanel" aria-labelledby="tab_main">
                <div class="card border-0">
                    <div class="card-body border-left border-right">
                        <form id="main_settings_form" method="post" autocomplete="off">
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
                                        <input id="setting_rest_toggle" class="form-check-input" type="checkbox" name="enable_rest">
                                        <label class="form-check-label" for="setting_rest_toggle">
                                            REST Server
                                        </label>
                                    </div>
                                    <div class="form-check">
                                        <input id="setting_tpm2net_toggle" class="form-check-input" type="checkbox" name="enable_tpm2net">
                                        <label class="form-check-label" for="setting_tpm2net_toggle">
                                            TPM2Net Server
                                        </label>
                                    </div>
                                </div>
                            </div>
                        </form>
                    </div>
                    <div class="card-footer border rounded-bottom">
                        <button type="submit" class="btn btn-primary float-right ml-2" form="main_settings_form">Save</button>
                        <a class="btn btn-danger float-right" href="/settings/reset/main">Reset</a>
                    </div>
                </div>
            </div>
            <div class="tab-pane" id="tab_pane_default_animation_pane" role="tabpanel" aria-labelledby="tab_default_animation">
                <!-- TODO: fill with default animation settings -->
            </div>
        </div>
    </div>
</div>

<script src="/js/post_request.js"></script>
<script>
    window.addEventListener("load", function(){
        setting_brightness_preview_btn.onclick = function() {
            // create a dynamic form object, that contains only the new brightness value
            var form_data = new FormData();
            form_data.append(setting_brightness_slider.name, setting_brightness_slider.value);

            // send the request
            post_request("/settings/set_brightness", form_data);
        }
    });
</script>
