# -*- coding: utf-8 --
from pydrive.drive import GoogleDrive
import usb
import cannery
import gdrive
import music_sync_utils
import sync
import sys
reload(sys)
sys.setdefaultencoding('utf8')

# IOREG device info pickle file
ioreg_file = "ioreg_file.p"

def main():
    # Drive Setup
    gauth = gdrive.login()
    drive = GoogleDrive(gauth)
    folder_name = 'Music'
    music_folder = gdrive.get_folder_from_root(drive, folder_name)

    # Create GoogleDriveCollection
    google_drive_library = music_sync_utils.MusicLibrary(music_folder.metadata['etag'])

    google_drive_library.collection = gdrive.get_google_drive_collection(drive, music_folder)
    google_drive_library.collection = music_sync_utils.clean_unicode(google_drive_library.collection)
    print "collection updated", google_drive_library

    print("Your Drive music takes up {0} Mib, {1} Gb of space.".format(google_drive_library.get_collection_size()/1024/1024, google_drive_library.get_collection_size()/1000/1000/1000))

    cannery.pickle_drive_library(google_drive_library, music_folder)

    # USB Setup Stuff
    ioreg_device = cannery.load_ioreg(ioreg_file)
    if not ioreg_device:
        ioreg_device = usb.pick_from_ioreg()
    df_device = usb.pick_from_df()

    # These two print statements should probably go elsewhere/nowhere
    print "You picked this device from IOREG: {}".format(ioreg_device)
    print "You picked this device from DF: {}".format(df_device)

    # Create, fill, and clean USBCollection
    usb_music = music_sync_utils.USBLibrary(df_device.mounted_on)
    usb_music.collection = usb.get_usb_collection(usb_music.file_path)
    usb_music.collection = music_sync_utils.clean_unicode(usb_music.collection)

    missing_from_usb = music_sync_utils.subtract_collection_elements(google_drive_library, usb_music)
    missing_from_drive = music_sync_utils.subtract_collection_elements(usb_music, google_drive_library)

    missing_from_drive_less = music_sync_utils.find_duplicate_albums(missing_from_usb, missing_from_drive)
    missing_from_usb_less = music_sync_utils.find_duplicate_albums(missing_from_drive, missing_from_usb)

    print "The following are missing from your USB device"
    music_sync_utils.print_collection(missing_from_usb_less.collection)
    print "The following are missing from your Drive"
    music_sync_utils.print_collection(missing_from_drive_less.collection)

    # Get albums to sync. Need artists too.
    gdrive_collection = sync.get_gdrive_artists_from_collection(drive, music_folder, missing_from_usb_less.collection)
    # gdrive_collection is a dict of artist_name: [drive_album]
    gdrive_sync_size = sync.get_size_of_syncing_collection(drive, gdrive_collection)
    print 'Size of GDrive files to be added (mb): ', gdrive_sync_size
    # watch out that size is hard coded against the df call - can return different things
    free_space_usb = int(df_device.avail)/1024.0
    print "Free space on USB (mb)", free_space_usb
    if free_space_usb < gdrive_sync_size:
        print "Not enough space on USB Device. Exiting..."
        sys.exit(0)
    free_space_pc = sync.get_free_space_on_local()
    print "Free space on PC  (mb)", free_space_pc
    if free_space_pc < gdrive_sync_size:
        sync.buffered_sync_gdrive_to_usb(drive, gdrive_collection, usb_music.file_path)
        print "Not enough space on laptop. Exiting..."
        sys.exit(0)

    # Download from Drive to USB
    #temp_music = '/Users/jgp/Dropbox/ProgrammingProjects/PyMusicSync/music_sync/temp_music/'
    print 'Buffered Sync'
    try:
        sync.buffered_sync_gdrive_to_usb(drive, gdrive_collection, usb_music.file_path)
    except:
        sync.delete_folder()

    #temp_music = sync.download_gdrive_locally(drive, music_folder, missing_from_drive_less.collection)
    #sync.sync_music_from_temp_to_USB(usb_music.file_path, temp_music)

    # We can pickle the IOREG stuff because its serial no. is invariant,
    # But we can't be sure that its mount point in df will be the same.
    # Need to research if there's a (reliable) link between df and IOREG
    cannery.pickle_ioreg(ioreg_device, ioreg_file)

if __name__ == '__main__':
    main() 
