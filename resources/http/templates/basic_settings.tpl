% rebase("base.tpl", title="Basic settings")

<div class="main_settings row justify-content-center">
    <div class="col">
        <form action="/basic_settings/set_brightness" method="post">
            <div class="form-group">
                <label for="brightness-form-container">Brightness</label>
                <div id="brightness-form-container" class="slider_container d-flex align-items-center">
                    <input class="custom-range slider flex-grow-1 mr-2"
                           style="width:1px"
                           name="brightness_value"
                           type="range"
                           min="0" max="100" value="{{current_brightness}}">
                    <span class="pr-2">
                        <span class="slider_value badge badge-warning" style="font-size:3ex;width:3em"></span>
                    </span>
                    <button class="btn btn-success" type="submit">Preview</button>
                </div>
            </div>
        </form>
    </div>
</div>
