<!-- CALLOSUM_METADATA={"link": "https://github.com/callosum-dot-app/callosum/blob/main/CONTRIBUTING.md"} -->

# Contributing to Callosum

Hey there! We are so excited that you're interested in Callosum.

As an open source project in a rapidly changing space, we welcome all contributions.

## 💃 Guidelines

### Contribution Opportunities

The [GitHub Issues](https://github.com/callosum-dot-app/callosum/issues) page is a great place to start for contribution ideas.

To ensure that your contribution is aligned with the project's direction, please reach out to any maintainer on the Callosum team
via [Discord](https://discord.gg/4NA5SbzrWb) or [email](mailto:hello@callosum.app).

Issues that have been explicitly approved by the maintainers (aligned with the direction of the project)
will be marked with the `approved by maintainers` label.
Issues marked `good first issue` are an especially great place to start.

**Connectors** to other tools are another great place to contribute. For details on how, refer to this
[README.md](https://github.com/callosum-dot-app/callosum/blob/main/backend/callosum/connectors/README.md).

If you have a new/different contribution in mind, we'd love to hear about it!
Your input is vital to making sure that Callosum moves in the right direction.
Before starting on implementation, please raise a GitHub issue.

Also, always feel free to message the founders (Chris Weaver / Yuhong Sun) on
[Discord](https://discord.gg/4NA5SbzrWb) directly about anything at all.

### Contributing Code

To contribute to this project, please follow the
["fork and pull request"](https://docs.github.com/en/get-started/quickstart/contributing-to-projects) workflow.
When opening a pull request, mention related issues and feel free to tag relevant maintainers.

Before creating a pull request please make sure that the new changes conform to the formatting and linting requirements.
See the [Formatting and Linting](#formatting-and-linting) section for how to run these checks locally.

### Getting Help 🙋

Our goal is to make contributing as easy as possible. If you run into any issues please don't hesitate to reach out.
That way we can help future contributors and users can avoid the same issue.

We also have support channels and generally interesting discussions on our
[Discord](https://discord.gg/4NA5SbzrWb).

We would love to see you there!

## Get Started 🚀

Callosum being a fully functional app, relies on some external software, specifically:

- [Postgres](https://www.postgresql.org/) (Relational DB)
- [Vespa](https://vespa.ai/) (Vector DB/Search Engine)
- [Redis](https://redis.io/) (Cache)
- [MinIO](https://min.io/) (File Store)
- [Nginx](https://nginx.org/) (Not needed for development flows generally)

> **Note:**
> This guide provides instructions to build and run Callosum locally from source with Docker containers providing the above external software. We believe this combination is easier for
> development purposes. If you prefer to use pre-built container images, we provide instructions on running the full Callosum stack within Docker below.

### Local Set Up

Be sure to use Python version 3.11. For instructions on installing Python 3.11 on macOS, refer to the [CONTRIBUTING_MACOS.md](./CONTRIBUTING_MACOS.md) readme.

If using a lower version, modifications will have to be made to the code.
If using a higher version, sometimes some libraries will not be available (i.e. we had problems with Tensorflow in the past with higher versions of python).

#### Backend: Python requirements

Currently, we use [uv](https://docs.astral.sh/uv/) and recommend creating a [virtual environment](https://docs.astral.sh/uv/pip/environments/#using-a-virtual-environment).

For convenience here's a command for it:

```bash
uv venv .venv --python 3.11
source .venv/bin/activate
```

_For Windows, activate the virtual environment using Command Prompt:_

```bash
.venv\Scripts\activate
```

If using PowerShell, the command slightly differs:

```powershell
.venv\Scripts\Activate.ps1
```

Install the required python dependencies:

```bash
uv sync --all-extras
```

Install Playwright for Python (headless browser required by the Web Connector):

```bash
uv run playwright install
```

#### Frontend: Node dependencies

Callosum uses Node v22.20.0. We highly recommend you use [Node Version Manager (nvm)](https://github.com/nvm-sh/nvm)
to manage your Node installations. Once installed, you can run

```bash
nvm install 22 && nvm use 22
node -v # verify your active version
```

Navigate to `callosum/web` and run:

```bash
npm i
```

## Formatting and Linting

### Backend

For the backend, you'll need to setup pre-commit hooks (black / reorder-python-imports).

Then run:

```bash
uv run pre-commit install
```

Additionally, we use `mypy` for static type checking.
Callosum is fully type-annotated, and we want to keep it that way!
To run the mypy checks manually, run `uv run mypy .` from the `callosum/backend` directory.

### Web

We use `prettier` for formatting. The desired version will be installed via a `npm i` from the `callosum/web` directory.
To run the formatter, use `npx prettier --write .` from the `callosum/web` directory.

Pre-commit will also run prettier automatically on files you've recently touched. If re-formatted, your commit will fail.
Re-stage your changes and commit again.

# Running the application for development

## Developing using VSCode Debugger (recommended)

**We highly recommend using VSCode debugger for development.**
See [CONTRIBUTING_VSCODE.md](./CONTRIBUTING_VSCODE.md) for more details.

Otherwise, you can follow the instructions below to run the application for development.

## Manually running the application for development
### Docker containers for external software

You will need Docker installed to run these containers.

First navigate to `callosum/deployment/docker_compose`, then start up Postgres/Vespa/Redis/MinIO with:

```bash
docker compose up -d index relational_db cache minio
```

(index refers to Vespa, relational_db refers to Postgres, and cache refers to Redis)

### Running Callosum locally

To start the frontend, navigate to `callosum/web` and run:

```bash
npm run dev
```

Next, start the model server which runs the local NLP models.
Navigate to `callosum/backend` and run:

```bash
uvicorn model_server.main:app --reload --port 9000
```

_For Windows (for compatibility with both PowerShell and Command Prompt):_

```bash
powershell -Command "uvicorn model_server.main:app --reload --port 9000"
```

The first time running Callosum, you will need to run the DB migrations for Postgres.
After the first time, this is no longer required unless the DB models change.

Navigate to `callosum/backend` and with the venv active, run:

```bash
alembic upgrade head
```

Next, start the task queue which orchestrates the background jobs.
Jobs that take more time are run async from the API server.

Still in `callosum/backend`, run:

```bash
python ./scripts/dev_run_background_jobs.py
```

To run the backend API server, navigate back to `callosum/backend` and run:

```bash
AUTH_TYPE=disabled uvicorn callosum.main:app --reload --port 8080
```

_For Windows (for compatibility with both PowerShell and Command Prompt):_

```bash
powershell -Command "
    $env:AUTH_TYPE='disabled'
    uvicorn callosum.main:app --reload --port 8080
"
```

> **Note:**
> If you need finer logging, add the additional environment variable `LOG_LEVEL=DEBUG` to the relevant services.

#### Wrapping up

You should now have 4 servers running:

- Web server
- Backend API
- Model server
- Background jobs

Now, visit `http://localhost:3000` in your browser. You should see the Callosum onboarding wizard where you can connect your external LLM provider to Callosum.

You've successfully set up a local Callosum instance! 🏁

#### Running the Callosum application in a container

You can run the full Callosum application stack from pre-built images including all external software dependencies.

Navigate to `callosum/deployment/docker_compose` and run:

```bash
docker compose up -d
```

After Docker pulls and starts these containers, navigate to `http://localhost:3000` to use Callosum.

If you want to make changes to Callosum and run those changes in Docker, you can also build a local version of the Callosum container images that incorporates your changes like so:

```bash
docker compose up -d --build
```


### Release Process

Callosum loosely follows the SemVer versioning standard.
Major changes are released with a "minor" version bump. Currently we use patch release versions to indicate small feature changes.
A set of Docker containers will be pushed automatically to DockerHub with every tag.
You can see the containers [here](https://hub.docker.com/search?q=callosum%2F).
