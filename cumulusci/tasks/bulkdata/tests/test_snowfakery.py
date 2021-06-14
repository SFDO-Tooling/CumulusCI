from cumulusci.tasks.bulkdata.snowfakery import UploadStatus


class XXXTestUploadStatus:  # FIX THESE TESTS
    def test_upload_status(self):
        u = UploadStatus(
            base_batch_size=5000,
            confirmed_count_in_org=20000,
            sets_being_generated=5000,
            sets_being_loaded=20000,
            sets_queued=0,
            target_count=30000,
            upload_queue_backlog=1,
            user_max_num_generator_workers=4,
            user_max_num_uploader_workers=15,
        )
        assert u.total_needed_generators == 1, u.total_needed_generators

        u = UploadStatus(
            base_batch_size=5000,
            confirmed_count_in_org=0,
            sets_being_generated=5000,
            sets_being_loaded=20000,
            sets_queued=0,
            target_count=30000,
            upload_queue_backlog=1,
            user_max_num_generator_workers=4,
            user_max_num_uploader_workers=15,
        )
        assert u.total_needed_generators == 1, u.total_needed_generators

        u = UploadStatus(
            base_batch_size=5000,
            confirmed_count_in_org=0,
            sets_being_generated=5000,
            sets_being_loaded=15000,
            sets_queued=0,
            target_count=30000,
            upload_queue_backlog=1,
            user_max_num_generator_workers=4,
            user_max_num_uploader_workers=15,
        )
        assert u.total_needed_generators == 2, u.total_needed_generators

        u = UploadStatus(
            base_batch_size=5000,
            confirmed_count_in_org=29000,
            sets_being_generated=0,
            sets_being_loaded=0,
            sets_queued=0,
            target_count=30000,
            upload_queue_backlog=0,
            user_max_num_generator_workers=4,
            user_max_num_uploader_workers=15,
        )
        assert u.total_needed_generators == 1, u.total_needed_generators

        u = UploadStatus(
            base_batch_size=5000,
            confirmed_count_in_org=4603,
            sets_being_generated=5000,
            sets_being_loaded=20000,
            sets_queued=0,
            target_count=30000,
            upload_queue_backlog=0,
            user_max_num_generator_workers=4,
            user_max_num_uploader_workers=15,
        )
        assert u.total_needed_generators == 1, u.total_needed_generators

        # TODO: In a situation like this, it is sometimes the case
        #       that there are not enough records generated to upload.
        #
        #       Due to internal striping, the confirmed_count_in_org
        #       could be correct and yet the org pauses while uploading
        #       other sobjects for several minutes.
        #
        #       Need to get rid of the assumption that every record
        #       that is created must be uploaded and instead make a
        #       backlog that can be either uploaded or discarded.

        #       Perhaps the upload queue should always be full and
        #       throttling should always happen in the uploaders, not
        #       the generators.
        u = UploadStatus(
            base_batch_size=500,
            confirmed_count_in_org=39800,
            sets_being_generated=0,
            sets_being_loaded=5000,
            sets_queued=0,
            target_count=30000,
            upload_queue_backlog=0,
            user_max_num_generator_workers=4,
            user_max_num_uploader_workers=15,
        )
        assert u.total_needed_generators == 1, u.total_needed_generators
