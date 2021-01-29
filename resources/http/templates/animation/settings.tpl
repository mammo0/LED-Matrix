% from server.http_server import Input


<form id="animation_settings_form_{{animation.animation_name}}" method="post" autocomplete="off">
    % if animation.animation_variants is not None:
        <div class="form-group">
            <label for="{{animation.animation_name}}_variant">
                <span class="icon bi-alt"></span>
                <span>Variant</span>
            </label>
            <select id="{{animation.animation_name}}_variant" class="custom-select" name="{{animation.animation_name}}_variant_value" autocomplete="off">
                %   for variant in animation.animation_variants:
                %       if variant == animation.animation_settings.variant:
                            <option value="{{variant.name}}" selected>{{variant.name.title()}} (Current)</option>
                %       else:
                            <option value="{{variant.name}}">{{variant.name.title()}}</option>
                %       end
                %   end
            </select>
        </div>
    % end
    % if animation.animation_parameters:
        <label for="parameter_container_{{animation.animation_name}}">
            <span class="icon bi-sliders"></span>
            <span>Paramter(s)</span>
        </label>
        <ul id="parameter_container_{{animation.animation_name}}" class="list-group bullet-list">
            <%
                for p_name, p_value in animation.animation_settings.parameter:
                    input = Input(p_value)
            %>
                    <li class="list-group-item bi-caret-right-fill m-0 p-0 border-0 pl-5">
                        <div class="form-group">

                            % if isinstance(input.value, bool):
                                <div class="form-check">
                                    <input id="{{animation.animation_name}}_parameter_{{p_name}}" type="{{input.type}}" class="form-check-input" name="{{animation.animation_name}}_parameter_{{p_name}}_value" {{"checked" if input.value else ""}}>
                                    <label class="form-check-label" for="{{animation.animation_name}}_parameter_{{p_name}}">
                                        {{p_name.replace("_", " ").title()}}
                                    </label>
                                </div>
                            % else:
                                <label for="{{animation.animation_name}}_parameter_{{p_name}}">
                                    {{p_name.replace("_", " ").title()}}
                                </label>
                                <input id="{{animation.animation_name}}_parameter_{{p_name}}" type="{{input.type}}" class="form-control" name="{{animation.animation_name}}_parameter_{{p_name}}_value" value="{{input.value}}">
                            % end
                        </div>
                    </li>
            %   end
        </ul>
    % end
    % if animation.is_repeat_supported:
        <div class="form-group">
            <label for="{{animation.animation_name}}_repeat">
                <span class="icon bi-arrow-repeat"></span>
                <span>Repeat</span>
            </label>
            <input id="{{animation.animation_name}}_repeat" type="number" class="form-control" name="{{animation.animation_name}}_repeat_value" min="-1" value="{{animation.animation_settings.repeat}}">
        </div>
    % end
</form>
