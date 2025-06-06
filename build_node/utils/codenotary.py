import os
import time
from logging import Logger
from typing import Dict, List, Optional, Tuple

from albs_build_lib.builder.models import Task
from albs_common_lib.utils.file_utils import (
    download_file,
    filter_files,
    hash_file,
)
from albs_common_lib.utils.rpm_utils import get_rpm_metadata
from immudb_wrapper import ImmudbWrapper


def notarize_build_artifacts(
    task: Task,
    artifacts_dir: str,
    immudb_client: ImmudbWrapper,
    build_host: str,
    logger: Optional[Logger] = None,
) -> Tuple[Dict[str, str], List[str]]:

    srpm_path = None
    artifact_paths = []
    for artifact_path in filter_files(
        artifacts_dir,
        lambda x: any(
            (x.endswith(_type) for _type in ('.log', '.cfg', '.rpm'))
        ),
    ):
        if artifact_path.endswith('.src.rpm'):
            srpm_path = artifact_path
        artifact_paths.append(artifact_path)

    cas_metadata = {
        'build_id': task.build_id,
        'build_host': build_host,
        'build_arch': task.arch,
        'built_by': task.created_by.full_name,
        'sbom_api_ver': '0.2',
    }
    if task.is_alma_source() and task.alma_commit_cas_hash:
        cas_metadata['alma_commit_sbom_hash'] = task.alma_commit_cas_hash
    if task.ref.git_ref:
        cas_metadata.update({
            'source_type': 'git',
            'git_url': task.ref.url,
            'git_ref': task.ref.git_ref,
            'git_commit': task.ref.git_commit_hash,
        })
    else:
        srpm_filename = 'initial.src.rpm'
        try:
            srpm_path = download_file(
                task.ref.url, os.path.join(artifacts_dir, srpm_filename)
            )
        except:
            pass
        if srpm_path:
            hdr = get_rpm_metadata(srpm_path)
            epoch = hdr['epoch'] if hdr['epoch'] else '0'
            srpm_nevra = (
                f"{epoch}:{hdr['name']}-{hdr['version']}-{hdr['release']}.src"
            )
            if task.srpm_hash:
                srpm_sha256 = task.srpm_hash
            else:
                srpm_sha256 = hash_file(srpm_path, hash_type='sha256')
            cas_metadata.update({
                'source_type': 'srpm',
                'srpm_url': task.ref.url,
                'srpm_sha256': srpm_sha256,
                'srpm_nevra': srpm_nevra,
            })
            os.remove(srpm_path)

    notarized_artifacts = {}
    max_notarize_retries = 5
    to_notarize = artifact_paths
    non_notarized_artifacts = artifact_paths
    rpm_header_fields = (
        'name',
        'epoch',
        'version',
        'release',
        'arch',
        'sourcerpm',
    )

    while non_notarized_artifacts and max_notarize_retries:
        non_notarized_artifacts = []
        for artifact in to_notarize:
            result = {}
            artifact_metadata = {}
            if artifact.endswith('.rpm'):
                artifact_metadata = cas_metadata.copy()
                rpm_header = get_rpm_metadata(artifact)
                for field in rpm_header_fields:
                    artifact_metadata[field] = rpm_header[field]
            result = immudb_client.notarize_file(
                artifact,
                user_metadata=(
                    artifact_metadata if artifact_metadata else cas_metadata
                ),
            )
            notarized = result.get('verified', False)
            cas_hash = result.get('value', {}).get('Hash')

            notarized_artifacts[artifact] = cas_hash
            if not notarized:
                non_notarized_artifacts.append(artifact)
                if logger and 'error' in result:
                    logger.error(
                        'Cannot notarize artifact: %s\nError: %s',
                        artifact,
                        result['error'],
                    )

        if non_notarized_artifacts:
            to_notarize = non_notarized_artifacts
            max_notarize_retries -= 1
            time.sleep(10)

    return notarized_artifacts, non_notarized_artifacts
