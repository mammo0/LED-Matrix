% setdefault("animations", {})
% setdefault("current_animation_name", "")

% rebase("base.tpl", page_title="Home")


<div class="row">
    <div class="col">
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
                    include("animation/selector.tpl", animations=animations,
                                                      current_animation_name=current_animation_name)
                %>
            </div>
            <div class="card-footer">
                <button id="btn_start_animation" type="submit" class="btn btn-primary float-right ml-3" formaction="/">
                    <span class="icon bi-play-fill"></span>
                    <span>Start</span>
                </button>
                <button id="btn_new_schedule_entry" type="submit" class="btn btn-primary float-right" formaction="/schedule/new">
                    <span class="icon bi-clock-fill"></span>
                    <span>Schedule</span>
                </button>
            </div>
        </div>
    </div>
</div>

<script>
    window.addEventListener("load", function(){
        function submit_animation_form(form_action) {
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
            animation_form.action = form_action;
            animation_form.submit();
        }

        btn_start_animation.onclick = function(){
            submit_animation_form(this.formAction);
        }
        btn_new_schedule_entry.onclick = function(){
            submit_animation_form(this.formAction);
        }
    });
</script>
