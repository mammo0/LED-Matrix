% rebase("base.tpl", title="Basic settings")

<h2>Brightness</h2>
<form action="/basic_settings/set_brightness" method="post">
    <div class="slider_container">
        <input class="slider"
               name="brightness_value"
               type="range"
               min="0" max="100" value="{{current_brightness}}">
        <div class="slider_value"></div>
    </div>
    <button type="submit">Preview</button>
</form>
