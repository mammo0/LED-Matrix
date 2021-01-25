% from server.http_server import Input


<label for="animation_selector">
    <b>Animation</b>
</label>
<select id="animation_selector" class="custom-select" autocomplete="off">
    %   for animation_name in animations:
    %       if animation_name == current_animation_name:
                <option value="{{animation_name}}" selected>{{animation_name.title()}} (Current)</option>
    %       else:
                <option value="{{animation_name}}">{{animation_name.title()}}</option>
    %       end
    %   end
</select>

<div class="my-3"></div>
<hr/>

% for animation_name, animation in animations.items():
    <div id="animation_settings_{{animation_name}}" class="{{"d-none" if animation_name != current_animation_name else ""}}">
        <form id="animation_settings_form_{{animation_name}}" method="post" autocomplete="off">
            % if animation.animation_variants is not None:
                <div class="form-group">
                    <label for="{{animation_name}}_variant">
                        <span class="icon bi-alt"></span>
                        <span>Variant</span>
                    </label>
                    <select id="{{animation_name}}_variant" class="custom-select" name="{{animation_name}}_variant_value" autocomplete="off">
                        %   for variant in animation.animation_variants:
                        %       if variant == animation.current_variant:
                                    <option value="{{variant.name}}" selected>{{variant.name.title()}} (Current)</option>
                        %       else:
                                    <option value="{{variant.name}}">{{variant.name.title()}}</option>
                        %       end
                        %   end
                    </select>
                </div>
            % end
            % if animation.animation_parameters:
                <label for="parameter_container_{{animation_name}}">
                    <span class="icon bi-sliders"></span>
                    <span>Paramter(s)</span>
                </label>
                <ul id="parameter_container_{{animation_name}}" class="list-group bullet-list">
                    <%
                        parameters = animation.current_parameter
                        if parameters is None:
                            parameters = animation.animation_parameters
                        end

                        for p_name, p_value in parameters:
                            input = Input(p_value)
                    %>
                            <li class="list-group-item bi-caret-right-fill m-0 p-0 border-0 pl-5">
                                <div class="form-group">

                                    % if isinstance(input.value, bool):
                                        <div class="form-check">
                                            <input id="{{animation_name}}_parameter_{{p_name}}" type="{{input.type}}" class="form-check-input" name="{{animation_name}}_parameter_{{p_name}}_value" {{"checked" if input.value else ""}}>
                                            <label class="form-check-label" for="{{animation_name}}_parameter_{{p_name}}">
                                                {{p_name.replace("_", " ").title()}}
                                            </label>
                                        </div>
                                    % else:
                                        <label for="{{animation_name}}_parameter_{{p_name}}">
                                            {{p_name.replace("_", " ").title()}}
                                        </label>
                                        <input id="{{animation_name}}_parameter_{{p_name}}" type="{{input.type}}" class="form-control" name="{{animation_name}}_parameter_{{p_name}}_value" value="{{input.value}}">
                                    % end
                                </div>
                            </li>
                    %   end
                </ul>
            % end
            % if animation.is_repeat_supported:
                <div class="form-group">
                    <label for="{{animation_name}}_repeat">
                        <span class="icon bi-arrow-repeat"></span>
                        <span>Repeat</span>
                    </label>
                    <input id="{{animation_name}}_repeat" type="number" class="form-control" name="{{animation_name}}_repeat_value" min="-1" value="{{animation.current_repeat_value if animation.current_repeat_value is not None else "0"}}">
                </div>
            % end
        </form>
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
