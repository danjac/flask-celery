import unittest2 as unittest

import flask

from flaskext import celery


class test_Celery(unittest.TestCase):

    def get_app(self, **kwargs):
        app = flask.Flask(__name__)
        default_config = dict(
            BROKER_TRANSPORT="memory",
        )
        app.config.update(default_config, **kwargs)
        return app

    def test_loader_is_configured(self):
        from celery.loaders import current_loader, load_settings
        loader = current_loader()
        self.assertIsInstance(loader, celery.FlaskLoader)
        settings = load_settings()
        self.assertTrue(loader.configured)

    def test_task_honors_app_settings(self):
        app = self.get_app(
            CELERY_IGNORE_RESULT=True,
            CELERY_TASK_SERIALIZER="msgpack",
        )
        c = celery.Celery(app)

        @c.task(foo=1)
        def add_task_args(x, y):
            return x + y

        @c.task
        def add_task_noargs(x, y):
            return x + y

        for task in add_task_args, add_task_noargs:
            self.assertTrue(any("BaseFlaskTask" in repr(cls)
                                for cls in task.__class__.mro()))
            self.assertEqual(task(2, 2), 4)
            self.assertEqual(task.serializer, "msgpack")
            self.assertTrue(task.ignore_result)

    def test_establish_connection(self):
        app = self.get_app()
        c = celery.Celery(app)
        Task = c.create_task_cls()
        conn = Task.establish_connection()
        self.assertIn("carrot.backends.queue", repr(conn.create_backend()))
        conn.connect()

    def test_apply(self):
        app = self.get_app()
        c = celery.Celery(app)

        @c.task
        def add(x, y):
            return x + y

        res = add.apply_async((16, 16))
        self.assertTrue(res.task_id)

        consumer = add.get_consumer()
        while True:
            m = consumer.fetch()
            if m:
                break
        self.assertEqual(m.payload["task"], add.name)

    def test_Worker(self):
        app = self.get_app()
        c = celery.Celery(app)
        worker = c.Worker()
        self.assertTrue(worker)

if __name__ == "__main__":
    unittest.main()
