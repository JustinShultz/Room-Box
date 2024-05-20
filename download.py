from pollination_streamlit_viewer import viewer

def download_output(api_key: str, owner: str, project: str, job_id: str, run_index: int,
                output_name: str, target_folder: str) -> None:
    """Download output from a job on Pollination.

    Args:
        api_key: The API key of the Pollination account.
        owner: The owner of the Pollination account.
        project: The name of the project inside which the job was created.
        job_id: The id of the job.
        run_index: The index of the run inside the job.
        output_name: The name of the output you wish to download. You can find the names
            of all the outputs either on the job page or on the recipe page.
        target_folder: The folder where the output will be downloaded.
    """
    out_job = Job(owner, project, job_id, client=api_client)
    run = out_job.runs[run_index]
    output = run.download_zipped_output(output_name)

    with zipfile.ZipFile(output) as zip_folder:
        zip_folder.extractall(target_folder)

out = download_output(
    owner= owner,
    project= project,
    job_id= '6aceb46e-9e35-4d5a-bf46-9f0b226ce0cc',
    run_index= 1,
    output_name='visualization.vtkjs',
    target_folder='./data/results',
    api_key=api_key
)

st.write(out)

if out is not None:
    vtkjs_path = pathlib.Path(out.target_folder + out.output_name)
    viewer(content=vtkjs_path.read_bytes(), key='df')