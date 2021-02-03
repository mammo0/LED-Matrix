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
                <button id="btn_start_animation" type="submit" class="btn btn-primary float-right ml-3" formaction="/" onclick="submit_animation_form(this.formAction);">
                    <span class="icon bi-play-fill"></span>
                    <span>Start</span>
                </button>
                <button id="btn_new_schedule_entry" type="submit" class="btn btn-primary float-right" formaction="/schedule/new" onclick="submit_animation_form(this.formAction);">
                    <span class="icon bi-clock-fill"></span>
                    <span>Schedule</span>
                </button>
            </div>
        </div>
    </div>
</div>

<script src="/js/animation_form.js"></script>
