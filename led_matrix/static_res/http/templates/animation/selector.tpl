% setdefault("animation_controllers", {})
% setdefault("current_animation_name", "")


<label for="animation_selector">
    <b>Animation</b>
</label>
<select id="animation_selector" class="custom-select" autocomplete="off">
    %   for animation_name in animation_controllers:
    %       if animation_name == current_animation_name:
                <option value="{{animation_name}}" selected>{{animation_name.title()}} (Current)</option>
    %       else:
                <option value="{{animation_name}}">{{animation_name.title()}}</option>
    %       end
    %   end
</select>

<div class="my-3"></div>
<hr/>

% for animation_name, animation_controller in animation_controllers.items():
    <div id="animation_settings_{{animation_name}}" class="{{"d-none" if animation_name != current_animation_name else ""}}">
        % include("animation/settings.tpl", animation_controller=animation_controller, animation_settings=animation_controller.settings)
    </div>
% end

<script>
    window.addEventListener("load", function(){
        var previos_selected_animation_name;

        // save the current selected animation on every focus event
        animation_selector.onfocus = function(){
            previos_selected_animation_name = animation_selector.value;
        }
        // on every change show the corresponding animation pane
        animation_selector.onchange = function(event){
            let new_selected_animation_name = animation_selector.value;
            if(new_selected_animation_name == previos_selected_animation_name){
                return;
            }

            let previous_animation_pane = document.getElementById("animation_settings_" + previos_selected_animation_name);
            let new_animation_pane = document.getElementById("animation_settings_" + new_selected_animation_name);

            previous_animation_pane.classList.add("d-none");
            new_animation_pane.classList.remove("d-none");

            previos_selected_animation_name = new_selected_animation_name;
        }
    });
</script>
