% from server.http_server import Input


% animation_obj = animations[animation_settings.animation_name]

<form id="animation_settings_form_{{animation_settings.animation_name}}" class="needs-validation" method="post" autocomplete="off">
    % if animation_obj.animation_variants is not None:
        <div class="form-group">
            <label for="{{animation_settings.animation_name}}_variant">
                <span class="icon bi-alt"></span>
                <span>Variant</span>
            </label>
            <select id="{{animation_settings.animation_name}}_variant" class="custom-select" name="{{animation_settings.animation_name}}_variant_value" autocomplete="off" required>
                % if animation_obj.accepts_dynamic_variant and len(animation_obj.animation_variants) == 0:
                    <option selected disabled value="">Please upload a Variant.</option>
                % else:
                    % for variant in animation_obj.animation_variants:
                        % if variant == animation_settings.variant:
                            <option value="{{variant.name}}" selected>{{variant.name.title()}}</option>
                        % else:
                            <option value="{{variant.name}}">{{variant.name.title()}}</option>
                        % end
                    % end
                % end
            </select>
            <div class="invalid-feedback">
                A variant must be selected.
            </div>
        </div>
    % end
    % if animation_obj.animation_parameters:
        <label for="parameter_container_{{animation_settings.animation_name}}">
            <span class="icon bi-sliders"></span>
            <span>Paramter(s)</span>
        </label>
        <ul id="parameter_container_{{animation_settings.animation_name}}" class="list-group bullet-list">
            <%
                for p_name, p_value in animation_settings.parameter:
                    input = Input(p_value)
            %>
                    <li class="list-group-item bi-caret-right-fill m-0 p-0 border-0 pl-5">
                        <div class="form-group">
                            % if isinstance(input.value, bool):
                                <div class="form-check">
                                    <input id="{{animation_settings.animation_name}}_parameter_{{p_name}}" type="{{input.type}}" class="form-check-input" name="{{animation_settings.animation_name}}_parameter_{{p_name}}_value" {{"checked" if input.value else ""}}>
                                    <label class="form-check-label" for="{{animation_settings.animation_name}}_parameter_{{p_name}}">
                                        {{p_name.replace("_", " ").title()}}
                                    </label>
                                </div>
                            % else:
                                <label for="{{animation_settings.animation_name}}_parameter_{{p_name}}">
                                    {{p_name.replace("_", " ").title()}}
                                </label>
                                <input id="{{animation_settings.animation_name}}_parameter_{{p_name}}" type="{{input.type}}" class="form-control" name="{{animation_settings.animation_name}}_parameter_{{p_name}}_value" value="{{input.value}}" required>
                                <div class="invalid-feedback">
                                    This value is required.
                                </div>
                            % end
                        </div>
                    </li>
            %   end
        </ul>
    % end
    % if animation_obj.is_repeat_supported:
        <div class="form-group">
            <label for="{{animation_settings.animation_name}}_repeat">
                <span class="icon bi-arrow-repeat"></span>
                <span>Repeat</span>
            </label>
            <input id="{{animation_settings.animation_name}}_repeat" type="number" class="form-control" name="{{animation_settings.animation_name}}_repeat_value" min="-1" value="{{animation_settings.repeat}}" required>
            <div class="invalid-feedback">
                This value is required.
            </div>
        </div>
    % end
</form>

<script src="/js/bootstrap_form_validation.js"></script>
