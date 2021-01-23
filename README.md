# filestorage
A Python library to make storing files simple and easy.

> :warning: Although there are extensive tests within this project for Python 3.6, 3.7, 3.8 and 3.9, it is a young project and there may be bugs and security holes. Be sure and test thoroughly prior to use in a production environment.

It is primarily intended to deal with file uploads to a static files directory or an object service like
[AWS S3](https://aws.amazon.com/s3/?nc2=h_ql_prod_st_s3) or [Linode](https://www.linode.com/products/object-storage/).
Files can by stored synchronously (for [WSGI](https://wsgi.readthedocs.io/en/latest/index.html) servers
like [Django](https://www.djangoproject.com/), [Flask](https://flask.palletsprojects.com/) or [Pyramid](https://trypyramid.com/)) or asynchronously
(for [ASGI](https://asgi.readthedocs.io/en/latest/) servers like [Starlette](https://www.starlette.io/),
[FastAPI](https://fastapi.tiangolo.com/) or [Django Channels](https://channels.readthedocs.io/en/stable/)).

Supports multiple storage services simultaneously or even the same service with multiple configurations.

Upload filters are easy to create and a few [are included](#filters) by default.

Table of Contents
=================

<!--ts-->
   * [filestorage](#filestorage)
   * [Table of Contents](#table-of-contents)
      * [Introduction](#introduction)
         * [Installation](#installation)
         * [The Store](#the-store)
            * [Configure the Store](#configure-the-store)
         * [Folders](#folders)
         * [Adding Filters](#adding-filters)
      * [Configuration](#configuration)
         * [Pyramid](#pyramid)
      * [Classes](#classes)
         * [StorageContainer](#storagecontainer)
         * [StorageHandler](#storagehandler)
         * [Filter](#filter)
         * [FileItem](#fileitem)
         * [Exceptions](#exceptions)
         * [Handlers](#handlers)
            * [LocalFileHandler](#localfilehandler)
            * [AsyncLocalFileHandler](#asynclocalfilehandler)
            * [S3Handler](#s3handler)
            * [DummyHandler](#dummyhandler)
            * [AsyncDummyHandler](#asyncdummyhandler)
         * [Filters](#filters)
            * [RandomizeFilename](#randomizefilename)
            * [ValidateExtension](#validateextension)
      * [Testing](#testing)

<!-- Added by: runner, at: Sat Jan 23 00:29:29 UTC 2021 -->

<!--te-->

## Introduction

### Installation

The library is available through the [Python Package Index](https://pypi.org/project/filestorage/) and can be installed with pip.

```bash
pip install filestorage
```

Different handlers have additional library requirements that can be optionally installed. For instance, the [async local file handler](#asynclocalfilehandler) requirements can be installed using:

```base
pip install "filestorage[aio_file]"
```

The extras are:
 * `aio_file` - requirements for async local file handling.
 * `s3` - requirements for storing to an AWS S3 bucket.

### The Store

Interaction with the library is primarily accomplished through a global [`store`](#storagecontainer) object. Any Python file can access this global object by importing it.

```python
from filestorage import store
store.finalized  # == False
```

> If you are uncomfortable by the existance of a global store, fear not! You can make a new instance of the store using the [StorageContainer](#storagecontainer) class. `my_store = StorageContainer()`, the use that in your program.

The store can hold multiple configurations that are accessed through its indices:

```python
store['portraits'].finalized  # == False
store['more']['and more'].finalized  # == False

PORTRAIT_STORE = store['portraits']  # global variable for later use!
```

The store and any of its other sub-configurations can be saved and referenced _prior_ to setting up any configuration.
This allows the store or any other sub-configuration to be imported anywhere and stored within global variables as
needed.

Trying to use the store to save files prior to providing it a handler will result in an error.

```python
store.save_data(filename='file.txt', data=b'spamity spam')

# FilestorageConfigError: No handler provided for store
```

So it's time to give it a [handler](#handler).

#### Configure the Store

Although any file can import the [store](#storagecontainer), it will not actually be usable until it is provided some kind of configuration.
You do this by giving the store a handler. This library includes a few kinds of [handlers](#handlers) with different configuration setups. For testing it's easiest to use the [DummyHandler](#dummyhandler):

```python
from filestore.handlers import DummmyHandler
store.handler = DummyHandler()
store['portraits'] = DummyHandler()
```

The DummyHandler doesn't need any other configuration and just stores any saved files in memory.

In your app, you would would normally perform this configuration after all files have been imported but before the app starts - for instance in an initialization step where the app configuration is read. Different frameworks (Pyramid/Django/Starlette) will have different mechanisms for this.

Now you can try to save some data into the store:

```python
store.save_data(filename='file.txt', data=b'spamity spam')

# 'file.txt' - the name of the file that was saved

store.exists(filename='file.txt')

# True
```

Handlers and filters might adjust the filename in the process of storing the file. The return value gives you feedback of the actual name of the file that was saved to the store. This might be useful for storing in a database for later reference.

You can set and reset the handler several times. When you want to lock in the configuration and prevent further changes, you need to finalize the store.
When you do so, all handlers and filters will validate their configuration and if any handlers are missing a configuration error will be thrown.  Any attempts to set a handler after this step will throw an error. This ensures that the store is properly set up once and only once.

```python
store.finalize_config()

store.handler = DummyHandler()
# FilestorageConfigError: Setting store.handler: store already finalized!
```

If using an ASGI server, you may need to instead use an [async startup task](https://www.starlette.io/events/) that contains:
```python
await store.async_finalize_config()
```

The finalization step also will validate any handler configuration.
For instance, the [local file handler](#localfilehandler) ensures its configured directory
exists, the [async file handler](#asynclocalfilehandler) ensures the proper libraries are installed and the S3 handler verifies the credentials by saving and deleting a dummy file in the bucket.

If the store or one of the sub-stores are not intended to be used, they must explicitly have their handler set to `None`. For instance, suppose
you want to use two different configurations, but don't want to use the store's base config. You can do:

```python
store['portraits'].handler = DummyHandler()
store['backgrounds'].handler = DummyHandler()

# Indicate that we don't want anybody using the base configurations (no `store.save_data()`)
store.handler = None

# Finalize the configuration to prevent further changes
store.finalize_config()
```

### Folders

The save/exists/delete methods can also be used on any sub-folder of the `store`.
```python
folder = store / 'one_folder' / 'another_folder'
folder.save_data(b'contents', 'file.txt')
```

Folders are late-binding and can thus be saved into a variable prior to the handler configuration.

If desired, a Folder can be used as a handler too:

```python
store.handler = DummyHandler()
store['portraits'].handler = store / 'portraits'
```

### Adding Filters

Filters allow mutating a file to be stored to a Handler. They are called in the order defined and a few filters are provided by this library.

For instance, it's often best not to simply store filenames provided by random Internet uploads. Although this library does scrub the filename, it's not as fool-proof as simply ignoring the provided filename and using a random string with a consistent length. The [RandomizeFilename](#randomizefilename) filter does just that.

```python
from filestorage.filters import RandomizeFilename
store.handler = DummyHandler(filters=[RandomizeFilename()])

store.save_data(filename='ignored name.txt', data=b'contents')
'5d29f7e1-50c0-4dc6-a466-b2ae042e8ac0.txt'
```

For more on filters, see the [Filter](#filter) class definition.

## Configuration

### Pyramid

This library can behave as a Pyramid plugin. When doing so, it will read from the Pyramid configuration and set up the handler(s) defined there. The `store` will also be available on the `request` object as `request.store`.

To set it up, include `filestorage.pyramid_config` in your configuration using the [Pyramid Configurator's include](.https://docs.pylonsproject.org/projects/pyramid/en/latest/api/config.html#pyramid.config.Configurator.include) method.

```python
from pyramid.config import Configurator

def main(global_config, **settings):
    config = Configurator()
    config.include('filestorage.pyramid_config'). # <---
    ...
```

Add any handler configuration to your app's config file. The handler and filters can refer to any handler or filter within `filestorage`, or can refer to any other package by full module path and model name.

```ini
[app:main]
# (other config settings)

# Base store with a custom handler and a custom filter
store.handler = myapp.filestorage.MyCustomHandler
store.filters[0] = myapp.filestorage.MyCustomFilter

# Portrait store with a couple of filestorage filters
store['portrait'].handler = LocalFileHandler
store['portrait'].handler.base_path = /var/www/static/uploaded_images
store['portrait'].handler.base_url = http://my.portraits/static
store['portrait'].handler.filters[0] = RandomizeFilename
store['portrait'].handler.filters[1] = ValidateExtension
store['portrait'].handler.filters[1].extensions = ['jpg', 'png']

# Another store that exists, but has been disabled.
store['not_used'].handler = None
```

Any parameters for filters and handlers are decoded and passed in as kwargs. Anything that looks like a list, set or dict literal is `eval`ed and bare whole numbers are converted to `int`. You can force anything to be a string by enclosing it in single or double quotes: `"50"`.

The store is then usable in any [view](https://docs.pylonsproject.org/projects/pyramid/en/latest/narr/views.html#defining-a-view-callable-as-a-function):

```python
def save_file(request):
    uploaded_file = request.POST['file']
    filename = request.store.save_field(uploaded_file)
    return Response(f'Saved to {filename}!')
```

Additional optional settings:
  * `store.request_property` - (Default `store`) - Name of the property to use on the request object. For example, set this to `my_store` then access the store through `request.my_store`.
  * `store.use_global` - (Default `True`) - Use the global `store` object. If set to `False` then the `request.store` object will independent of the global `store` object.

## Classes

### StorageContainer

This is the class for the global `store` object.

Methods:

 * `handler` - Gets the configured handler or raises an exception of no handler has been provided. Set this property to set the handler.
 * `sync_handler` - Gets the configured handler as a sync-only handler. Raises an exception if no `handler` has been set.
 * `async_handler` - Gets the configured handler as an async-only handler. Raises an exception if no `handler` has been set or if the configured handler can't be used asynchronously.
 * `finalize_config()` - Walk through all configured objects and check to ensure they have a valid configuration. Lock the `StorageContainer` to prevent any further configuration changes. Will raise a `FilestorageConfigError` if there's a configuration problem.
 * `async_finalize_config()` - awaitable version of the above call. Necessary for ASGI servers.
 * `finalized` - `True` if the config has been finalized, `False` otherwise.
 * `do_not_use` - `True` if the `handler` has been set to `None`, `False` otherwise.
 * `name` - String name of how this configuration is accessed. `store['a'].name == "['a']"`.
 * `[*]` - Get a sub-configuration object. Raises a `FilestorageConfigError` if the configuration is finalized and this configuration's `handler` hasn't been set.
 * `/ 'name'` - Obtain a `Folder` object with the same save/exist/delete methods as this object which write to the named sub-folder.

Once the handler is set, the store object can be used as a `StorageHandler` object.

### StorageHandler
(`StorageHandlerBase` or `AsyncStorageHandlerBase`)

All handlers inherit from `StorageHandlerBase`.

The async version of the Handler can be used for either synchronous or asynchronous operations. The `StorageHandlerBase` by itself can only be used for synchronous operations and any `async_*` method calls will throw an error. To make a new custom handler, start with the [handler template](../master/filestorage/handlers/_template.py).

> :warning: __Ensure your forms include the attribute enctype=”multipart/form-data”__ or your uploaded files will be empty. [Short example](https://html.com/attributes/form-enctype/) and [more detail](https://developer.mozilla.org/en-US/docs/Web/API/FormData/Using_FormData_Objects#sending_files_using_a_formdata_object).

Parameters:

 * `base_url` - Optional string - The URL prefix for any saved file. For example: `'https://eppx.com/static/'`. If not set, the `get_url` method will only return the path string, not the full URL.
 * `path` - Optional list or string - The path within the store (and URL) for any saved file. For example: `['folder', 'subfolder']`
 * `filters` - Optional list of [Filters](#all-filters) to apply, in order, when saving any file through this handler. For example: `[RandomizeFilename()]`

Methods:

 * `get_url(filename: str)` - Return the full URL of the given filename. If the `base_url` parameter isn't set, will only return the path string instead of the full URL.
 * `sanitize_filename(filename: str)` - Return the string stripped of dangerous characters.
 * Synchronous methods:
   * `exists(filename: str)` - `True` if the given file exists in the store, false otherwise.
   * `delete(filename: str)` - Deletes the given file from the store.
   * `save_file(filename: str, data: BinaryIO)` - Save the binary IO object to the given file.
   * `save_data(filename: str, data: bytes)` - Save the binary data to the given file.
   * `save_field(field: cgi.FieldStorage)` - Save the given field storage object.
 * Asynchronous methods: (all will throw a `FilestorageConfigError` if the handler doesn't support async operations.)
   * `async_exists(filename: str)` - Awaitable version
   * `async_delete(filename: str)` - Awaitable version
   * `async_save_file(filename: str, data: BinaryIO)` - Awaitable version
   * `async_save_data(filename: str, data: binary)` - Awaitable version
   * `async_save_field(field: cgi.FieldStorage)` - Awaitable version

Abstract Methods to be overridden when sub-classing:

 * `_validate()` - Check to ensure the provided configuration is correct. Can be an async method or return a `Future` object.
 * Synchronous methods: (All get passed a [FileItem](#fileitem) object)
   * `_exists(item: FileItem)` - Returns `True`/`False` to indicate if the item exists in the storage container.
   * `_delete(item: FileItem)` - Remove the item from the storage container.
   * `_save(item: FileItem)` - Save the item to the storage container and return the name of the file saved.
 * Asynchronous methods:
   * `async _async_exists(item: FileItem)` - async version, returns `True` or `False`.
   * `async _async_delete(item: FileItem)` - async version.
   * `async _async_save(item: FileItem)` - async version, returns the stored filename.

### Filter

The `FilterBase` is used as a base class for any Filters. These are not intended to be used directly, but to be passed as an optional list to a Handler through the `filters` parameter. To make a new custom filter, start with the [filter template](../master/filestorage/filters/_template.py).

Properties:

 * `async_ok` - `True`/`False` to indicate if this Filter is OK to be used asynchronously.

Methods:

 * `call(item: FileItem)` - Returns the filtered [FileItem](#fileitem).
 * `async_call(item: FileItem)` - Awaitable version of `call`. If the filter can't be used asynchronously, will raise a `FilestorageConfigError`.
 * `validate()` - Checks to ensure the Filter is configured correctly. Might return an Awaitable.

Abstract Methods to be overridden when sub-classing:

 * `_apply(item: FileItem)` - Returns the filtered [FileItem](#fileitem). It can optionally be an async method that will be awaited on. Can raise an exception if the item fails the filter.
 * `_validate()` - Check to ensure the provided configuration is correct. Can be an async method or return a `Future` object.

### FileItem

This is the basic item that's passed through Filters to the Handlers. It is based on a NamedTuple and is therefore immutable.

Parameters, which are also Properties:
 * `filename` - String
 * `path` - Optional tuple of the path under which the `filename` can be accessed or stored. Example: `('folder', 'subfolder')`.
 * `data` - Optional [BinaryIO](https://docs.python.org/3/library/typing.html#typing.BinaryIO) of the contents to store. Example: `BytesIO(b'contents')`.
 * `media_type` - Optional string describing the [media (or MIME) type](https://developer.mozilla.org/en-US/docs/Web/HTTP/Basics_of_HTTP/MIME_types) contained within the data. If not provided, the type will be [guessed](https://docs.python.org/3/library/mimetypes.html#mimetypes.guess_type) as needed based on the filename's extension.

Properties:
 * `url_path` - Relative path and filename for use in a URL. Example: `'folder/subfolder/file.txt'`
 * `fs_path` - Relative path and filename for use in the local filesystem. Example when running on Windows: `'folder\subfolder\file.txt'`.
 * `has_data` - `True` if data is populated.
 * `content_type` - String indicating the `media_type` to be used in HTTP headers as needed.

Methods:
 * `copy(**kwargs)` - Create a copy of this object, overriding any specific parameter. Example: `item.copy(filename='new_name.txt')`. This is very useful in a Filter that changes the filename or other properties.
 
Context Manager:

The FileItem can be used as a context manager, where it will modify the read/seek methods of the underlying object to fit the requested stream as necessary - either sync or async.

 * `with FileItem as f` - Returns an object (`f`) that behaves as an open file. `f.read()` and `f.seek()` methods are supported.
 * `async with FileItem as f` - Returns an object (`f`) that behaves as an async open file. `await f.read()` and `await f.seek()` methods are supported.

### Exceptions

All are importable via the `exceptions` sub-package. For example:

```python
from filestorage.exceptions import FilestorageError
```

 * FilestorageError - Base class for any exceptions raised by this library.
 * FileNotAllowed - The provided file is not allowed, either through a [Filter](#filter) or from a [Handler](#handler).
 * FileExtensionNotAllowed - The provided file with the given extension is not allowed, either through a [Filter](#filter) or from a [Handler](#handler).
 * FilestorageConfigError - There was some problem with the configuration.

### Handlers

All handlers are subclasses of the [StorageHandler](#storagehandler) class. These can be imported via the `handlers` sub-package. For example:

```python
from filestorage.handlers import LocalFileHandler

store.handler = LocalFileHandler(base_path='/home/www/uploads`)
```

#### LocalFileHandler

Store files on the local file system using synchronous methods.

Async not OK.

Parameters:
 * `base_path` - Where to store the files on the local filesystem
 * `auto_make_dir` - Automatically create the directory as needed.

#### AsyncLocalFileHandler

Store files on the local file system using asynchronous methods.

Async OK.

> :warning: __Requires the `aiofiles` library__, which will be installed with `pip install filestorage['aio_file']`

Parameters:
 * `base_path` - Where to store the files on the local filesystem
 * `auto_make_dir` (defualt: `False`)- Automatically create the directory as needed.
 * `allow_sync_methods` (default: `True`) - When `False`, all synchronous calls throw a `RuntimeError`. Might be helpful in preventing accidentally using the sync `save`/`exists`/`delete` methods, which would block the async loop too.

#### S3Handler

Store files to an S3 bucket. This handler works for synchronous and asynchronous calls.

Async OK.

> :warning: __Requires the `aioboto3` library__, which will be installed with `pip install filestorage['s3']`

> :warning: __Requires appropriate AWS permissions to the S3 bucket.__

Parameters:
 * `bucket_name` - required - AWS bucket to store the files in.
 * `acl` (default: `'public-read'`) - Access-Control to apply to newly saved files. Other interesting options are `'private'`, `'authenticate-read'`, and `'bucket-owner-read'`. See [the S3 documentation](https://docs.aws.amazon.com/AmazonS3/latest/dev/acl-overview.html#canned-acl) for more information.
 * `connect_timeout` (default: `5`) - Seconds to wait for a connection event before timeout.
 * `num_retries` (default: `5` - How many times the library will attempt to connect before failing.
 * `read_timeout` (default: `10`) Seconds to wait for a read event before timeout.
 * `keepalive_timeout` (default: `12`) - Send a packet every few seconds to keep active connections open.
 * `host_url` - When using [non-AWS S3 service](https://www.google.com/search?q=s3+compatible+storage) (like [Linode](https://www.linode.com/products/object-storage/)), use this url to connect. (Example: `'https://us-east-1.linodeobjects.com'`)
 * `region_name` - Overrides any region_name defined in the [AWS configuration file](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/configuration.html#using-a-configuration-file) or  the `AWS_DEFAULT_REGION` environment variable. Required if using AWS S3 and the value is not already set elsewhere.
 * `addressing_style` - Overrides any S3.addressing_style set in the [AWS configuration file](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/configuration.html#using-a-configuration-file).
 * `allow_sync_methods` (default: `True`) - When `False`, all synchronous calls throw a `RuntimeError`. Might be helpful in preventing accidentally using the sync `save`/`exists`/`delete` methods, which would block the async loop too.

Permissions can be configured in three different ways. They can be stored in environment variables, then can be stored in a particular AWS file, or they can be passed in directly.

See the [boto3 credentials documentation](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/credentials.html) for details on how to configure the required keys.

> :warning: __Do not hard-code secret information in your source code!__

If you wish to directly provide the connection information to this handler, use the following optional parameters:

 * `aws_access_key_id` - or use the `AWS_ACCESS_KEY_ID` environment variable.
 * `aws_secret_access_key` - or use the `AWS_SECRET_ACCESS_KEY` environment variable.
 * `aws_session_token` - Unnecessary when using the two previous options, but here for completeness. Note that [session tokens](https://docs.aws.amazon.com/cli/latest/reference/sts/get-session-token.html) have a maximum age of 36 hours. Could instead use the `AWS_SESSION_TOKEN` environment variable.
 * `profile_name` - Which profile to use within a [shared credentials file](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/credentials.html#shared-credentials-file).

#### DummyHandler

Handler used to test the file store - keeps any stored files in memory.

Async not OK - will fail for any async call. For an async version use the [AsyncDummyHandler](#asyncdummyhandler).

Accepts no parameters.

Properties:

 * `files` - a dictionary of all saved files. The key is the path/filename string and the value is a [FileItem](@fileitem) object.
 * `validated` - `True` if the handler was validated (which happens while finalizing the config).
 * `last_save` - The last [FileItem](@fileitem) saved.
 * `last_delete` - The last [FileItem](@fileitem) deleted.

Methods:

 * `assert_exists(filename: str, path: Tuple[str, ...]` - Asserts that the provided filename and path have been saved.
 * `assert_file_contains(filename: str, path: Tuple[str, ...], data: bytes)` - Asserts that the saved file contains the given data.

#### AsyncDummyHandler

Identical to the [DummyHandler](#dummyhandler), but can be used asynchronously.

### Filters

All are importable via the `filters` sub-package. For example:

```python
from filestorage.filter import RandomizeFilename

store.handler = DummyHandler(filters=[RandomizeFilename()])
```

#### RandomizeFilename

Filter to randomize the filename. It keeps any extension within the filename, but replaces the name with a random string.

Async OK.

Parameters:
 * `name_generator` Optional method that takes the filename (without extension) and returns a new random name. When left off, this Filter uses the [uuid4](https://docs.python.org/3/library/uuid.html#uuid.uuid4) method.

#### ValidateExtension

Reject any filename that does not have one of the indicated extensions. Raises a [`FileExtensionNotAllowed`](#exceptions) for a disallowed extension.

Async OK.

Parameters:
 * `extensions` - List of exceptions to allow through this filter. Example: `['jpg', 'png']`

## Testing

The [DummyHandler](#dummyhandler) or [AsyncDummyHandler](#asyncdummyhandler) are great tools for testing your application. To keep your tests isolated, you can create a new [store](#storagecontainer) object and configure it for each test as needed.

```python
from filestorage import StorageContainer
from filestorage.handlers import AsyncDummyHandler

def test_store():
    store = StorageContainer()
    dummy_handler = AsyncDummyHandler()
    store.handler = dummy_handler

    # Do whatever should trigger your app to store a file

    dummy_handler.assert_exists('name.txt', ('folder', 'subfolder'))
```

If you need to write several tests and want to check the result, it's probably best to create a couple of simple fixtures and allow [pytest](https://docs.pytest.org/en/stable/fixture.html) to inject them as needed.

Within `tests/conftest.py`:
```python
import pytest

from filestorage import StorageContainer
from filestorage.handlers import AsyncDummyHandler

@pytest.fixture
def dummy_handler():
    return AsyncDummyHandler()

@pytest.fixture
def store(dummy_handler):
    store = StorageContainer()
    store.handler = dummy_handler
    store.finalize_config()
    return store
```

Within `tests/test_myapp.py`
```python
def test_store(store, dummy_handler):
    # The configured dummy handler and store were auto-created and passed in here

    # Do whatever should trigger your app to store a file

    dummy_handler.assert_exists('name.txt', ('folder', 'subfolder'))
