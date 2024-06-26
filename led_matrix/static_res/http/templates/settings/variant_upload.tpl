% from bottle import request

% setdefault("animation_controllers", {})


<div class="accordion" id="dynamic_variant_selector">
    % for animation_name, animation_controller in animation_controllers.items():
        % if animation_controller.accepts_dynamic_variant:
            <div class="card">
                <div class="card-header" id="dynamic_variant_header_{{animation_name}}">
                    <h2 class="mb-0">
                        <button class="btn btn-link btn-block text-left" type="button" data-toggle="collapse" data-target="#dynamic_variant_body_{{animation_name}}" aria-expanded="false" aria-controls="dynamic_variant_body_{{animation_name}}">
                            {{animation_name.title()}}
                        </button>
                    </h2>
                </div>

                <div id="dynamic_variant_body_{{animation_name}}" class="collapse {{"show" if request.query.show_animation == animation_name else ""}}" aria-labelledby="dynamic_variant_header_{{animation_name}}" data-parent="#dynamic_variant_selector">
                    <div class="card-body">
                        <table class="table table-striped mb-5">
                            <thead class="thead-light">
                                <tr>
                                    <th scope="col">Current Variants</th>
                                    <th scope="col">Delete</th>
                                </tr>
                            </thead>
                            <tbody>
                                % for variant in animation_controller.variant_enum:
                                    <tr>
                                        <td>{{variant.name.title()}}</td>
                                        <td>
                                            <a class="btn btn-danger" href="/settings/variant_upload/{{animation_name}}/delete/{{variant.name}}">
                                                <span class="icon bi-trash-fill"></span>
                                                <span class="d-none d-sm-inline">Delete</span>
                                            </a>
                                        </td>
                                    </tr>
                                % end
                            </tbody>
                        </table>

                        <form class="needs-validation" method="post" autocomplete="off" action="/settings/variant_upload/{{animation_name}}/upload" enctype="multipart/form-data" novalidate>
                            <div class="form-group">
                                <label for="variant_upload_{{animation_name}}">Upload a new Variant</label>
                                <input type="file" class="form-control-file" id="variant_upload_{{animation_name}}" name="variant_upload_{{animation_name}}_value" required>
                                <div class="invalid-feedback">
                                    Please provide a file.
                                </div>
                            </div>
                            <button type="submit" class="btn btn-primary">
                                <span class="icon bi-upload"></span>
                                <span>Upload</span>
                            </button>
                        </form>
                    </div>
                </div>
            </div>
        % end
    % end
</div>

<script src="/js/bootstrap_form_validation.js"></script>
