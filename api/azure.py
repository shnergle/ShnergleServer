import os

# from azure.storage import BlobService


def store(*args):
    pass
    
def retrieve(*args):
    pass

# def store(image, entity, entity_id):
#     blob_service = BlobService(account_name='shnergledata',
#                                account_key=os.environ['BLOB_KEY'])
#     myblob = image.read()
#     name = '/' + entity + '/' + entity_id
#     blob_service.put_blob('images', name, myblob, x_ms_blob_type='BlockBlob')
#     return True
# 
# 
# def retrieve(entity, entity_id):
#     blob_service = BlobService(account_name='shnergledata',
#                                account_key=os.environ['BLOB_KEY'])
#     name = '/' + entity + '/' + entity_id
#     blob = blob_service.get_blob('images', name)
#     return blob
