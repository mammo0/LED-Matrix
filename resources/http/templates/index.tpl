% rebase("base.tpl", title="Home")


<div class="card">
    <div class="card-header d-flex align-items-baseline justify-content-between">
        <div>
            <span class="icon bi-play-fill"></span>
            <span>New Animation</span>
        </div>
        <a class="btn btn-danger" href="/stop-animation">
            <span class="icon bi-stop-fill"></span>
            <span class="d-none d-sm-inline">Stop Current Animation</span>
            <span class="d-inline d-sm-none">Current</span>
        </a>
    </div>
    <div class="card-body">
        <%
            include("animation_settings.tpl", animations=animations,
                                              current_animation_name=current_animation_name)
        %>
    </div>
    <div class="card-footer border rounded-bottom">
        <button id="btn_save_default_animation" type="submit" class="btn btn-primary float-right">
            <span class="icon bi-play-fill"></span>
            <span>Start</span>
        </button>
    </div>
</div>

<script>
    window.addEventListener("load", function(){
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
            animation_form.action = "/"
            animation_form.submit();
        }
    });
</script>
