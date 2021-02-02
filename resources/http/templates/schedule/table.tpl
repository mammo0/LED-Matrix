% setdefault('page_title', 'Schedule Table')
% setdefault('schedule_table', [])

% rebase("base.tpl", page_title=page_title)


<div class="row">
    <div class="col">
        <table class="table table-striped">
            <thead class="thead-light">
                <tr>
                    <th scope="col">#</th>
                    <th scope="col">Animation</th>
                    <th scope="col">Edit</th>
                    <th scope="col">Delete</th>
                </tr>
            </thead>
            <tbody>
                % for num, entry in enumerate(schedule_table, start=1):
                    <tr>
                        <th scope="row">{{num}}</th>
                        <td>{{entry.ANIMATION_SETTINGS.animation_name.title()}}</td>
                        <td>
                            <a class="btn btn-primary" href="/schedule/edit/{{entry.JOB_ID}}">
                                <span class="icon bi-pencil-fill"></span>
                                <span class="d-none d-sm-inline">Edit</span>
                            </a>
                        </td>
                        <td>
                            <a class="btn btn-danger" href="/schedule/delete/{{entry.JOB_ID}}">
                                <span class="icon bi-trash-fill"></span>
                                <span class="d-none d-sm-inline">Delete</span>
                            </a>
                        </td>
                    </tr>
                % end
            </tbody>
        </table>
    </div>
</div>
