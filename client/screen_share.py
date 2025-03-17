import pyautogui
import io
from PIL import Image
import base64
import threading
import logging
from protocol import Protocol
import constants



def split_and_send_screen(server_udp_addr, client_udp, userinfo, frame_id, img_bytes):
    """Split the screen data into chunks and send them to the server."""
    total_chunks = (len(img_bytes) // constants.PACKET_SIZE) + 1
    for chunk_id in range(total_chunks):
        chunk = img_bytes[chunk_id * constants.PACKET_SIZE : (chunk_id + 1) * constants.PACKET_SIZE]
        packet = Protocol("SCREEN_DATA_CHUNK", userinfo, {"frame_id": frame_id, "total_chunks": total_chunks, "chunk_id": chunk_id, "chunk": chunk}).to_str().encode('utf-8')
        client_udp.sendto(packet, server_udp_addr)

        



def capture_and_send_screen(frame_id, client_udp, server_udp_addr, userinfo):
    """Capture the screen and send it to the server."""
    """frame_id = 0
    while self.is_sharing_screen:"""
    print("Sharing screen")
    try:
        #frame_id += 1
        # Capture the screen
        screenshot = pyautogui.screenshot()

        # Resize the screenshot
        try:
            # For Pillow >= 10.0.0
            resampling_filter = Image.Resampling.LANCZOS
        except AttributeError:
            # For Pillow < 10.0.0
            resampling_filter = Image.ANTIALIAS

        screenshot = screenshot.resize((800, 600), resampling_filter)  # Resize to 800x600

        # Convert the screenshot to bytes
        img_byte_arr = io.BytesIO()
        screenshot.save(img_byte_arr, format='JPEG', quality=50)  # Lower quality
        img_byte_arr = img_byte_arr.getvalue()

        # Encode the image data as Base64
        img_base64 = base64.b64encode(img_byte_arr).decode('utf-8')

        # Capture sound if sound sharing is enabled
        
        # Send the screen data (and sound data if applicable) to the server
        """self.client.sendall(Protocol("SCREEN_DATA", username, {
            "image_data": img_base64,
        }).to_str().encode('utf-8'))
        """
        split_and_send_screen(server_udp_addr, client_udp, userinfo, frame_id, img_base64)
        # Send the screen data to the server
        #self.client.sendall(Protocol("SCREEN_DATA", username, {"image_data": img_base64}).to_str().encode('utf-8'))

        
    except Exception as e:
        logging.error(f"Error capturing or sending screen: {e}")
        raise(e)
        