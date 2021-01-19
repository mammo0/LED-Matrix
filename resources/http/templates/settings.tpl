% rebase("base.tpl", title="Basic settings")

<div class="main_settings row justify-content-center">
    <div class="col">
        <div class="card">
            <div class="card-header">
                <h3 class="m-0">Main</h3>
            </div>
            <div class="card-body">
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
                        <label for="setting_display_width">Display Width</label>
                        <input id="setting_display_width"
                               class="form-control"
                               type="number"
                               min="1">
                    </div>
                    <div class="form-group">
                        <label for="setting_display_height">Display Height</label>
                        <input id="setting_display_height"
                               class="form-control"
                               type="number"
                               min="1">
                    </div>
                </form>
            </div>
            <div class="card-footer">
                <button type="submit" class="btn btn-primary float-right" form="main_settings_form">Save</button>
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
