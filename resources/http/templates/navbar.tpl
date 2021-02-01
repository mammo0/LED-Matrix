% setdefault("brand_title", "LED-Matrix")
% setdefault("page_title", "Home")


<nav class="navbar navbar-expand navbar-dark bg-dark">
    <div class="container">
        <span class="navbar-brand mb-0 h1">
            <span style="font-variant: small-caps !important;">{{brand_title}}</span>
            <span class="font-weight-light">></span>
            <strong>{{page_title}}</strong>
        </span>
        <div class="collapse navbar-collapse" id="navbarNav">
            <ul class="navbar-nav">
                <li class="nav-item active">
                    <a class="nav-link" href="/">
                        <span class="icon bi-house-door-fill"></span>
                        <span class="d-none d-sm-inline">Home</span>
                    </a>
                </li>
            </ul>
            <ul class="navbar-nav ml-auto">
                <li class="nav-item active">
                    <a class="nav-link" href="/settings">
                        <span class="icon bi-gear-fill"></span>
                        <span class="d-none d-sm-inline">Settings</span>
                    </a>
                </li>
            </ul>
        </div>
    </div>
</nav>
