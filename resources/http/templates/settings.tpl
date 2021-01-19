% rebase("base.tpl", title="Basic settings")

<div class="main_settings row justify-content-center">
    <div class="col">
        <div class="card">
            <div class="card-header">
                <h3 class="m-0">Main</h3>
            </div>
            <div class="card-body">
                <form id="main-settings-form" method="post">
                    <div class="form-group">
                        <label for="setting-brightness-container">Brightness</label>
                        <div id="setting-brightness-container" class="slider_container d-flex align-items-center">
                            <input class="custom-range slider flex-grow-1 mr-2"
                                   style="width:1px"
                                   name="brightness_value"
                                   type="range"
                                   min="0" max="100" value="{{current_brightness}}">
                            <span class="pr-2">
                                <span class="slider_value badge badge-warning" style="font-size:3ex;width:3em"></span>
                            </span>
                            <button class="btn btn-success">Preview</button>
                        </div>
                    </div>
                    <div class="form-group">
                        <label for="setting-display-width">Display Width</label>
                        <input id="setting-display-width"
                               class="form-control"
                               type="number"
                               min="1">
                    </div>
                    <div class="form-group">
                        <label for="setting-display-height">Display Height</label>
                        <input id="setting-display-height"
                               class="form-control"
                               type="number"
                               min="1">
                    </div>
                </form>
            </div>
            <div class="card-footer">
                <button type="submit" class="btn btn-primary float-right" form="main-settings-form">Save</button>
            </div>
        </div>
    </div>
</div>
