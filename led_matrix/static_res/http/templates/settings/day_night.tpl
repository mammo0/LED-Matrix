<%
    if type == "day":
        brightness_value = config.main.day_brightness
        color_temp_value = config.main.day_color_temp
    else:
        brightness_value = config.main.night_brightness
        color_temp_value = config.main.night_color_temp
    end
%>

<li class="list-group-item m-0 p-0 border-0 pl-5">
    <div class="form-group">
        <label class="d-flex align-items-baseline justify-content-between" for="setting_{{type}}_brightness_container">
            <span>Brightness</span>
            <a class="btn btn-success" onclick="preview_brightness(setting_{{type}}_brightness_slider.value);">Preview</a>
        </label>
        <div id="setting_{{type}}_brightness_container" class="slider-container d-flex align-items-center">
            <input id="setting_{{type}}_brightness_slider"
                class="custom-range slider flex-grow-1 mr-2"
                style="width:1px"
                name="{{type}}_brightness_value"
                type="range"
                min="0" max="100" value="{{brightness_value}}">
            <span class="slider-value badge badge-warning" style="font-size:3ex;width:3em"></span>
        </div>
    </div>
    </li>
<li class="list-group-item m-0 p-0 border-0 pl-5">
    <div class="form-group">
        <label class="d-flex align-items-baseline justify-content-between" for="setting_{{type}}_color_temp_container">
            <span>Color Temperature</span>
            <a class="btn btn-success" onclick="preview_color_temp(setting_{{type}}_color_temp.value);">Preview</a>
        </label>
        <div id="setting_{{type}}_color_temp_container">
            <select id="setting_{{type}}_color_temp" class="custom-select" autocomplete="off" name="{{type}}_color_temp_value">
                % for k in ColorTemp:
                    <option value="{{k.name}}" {{"selected" if k == color_temp_value else ""}}>{{k.title}}</option>
                % end
            </select>
        </div>
    </div>
</li>
