# Exporting and Using the AI Inpainting API

This guide explains how to use the AI inpainting functionality as a standalone API service, making it accessible to external applications like those developed in Xcode for iOS and macOS.

## 1. How It Works

The `api_server.py` script acts as a wrapper around the core `diffusionbee_backend.py` engine. It starts a Flask web server that exposes a simple HTTP endpoint. When a request is received, it translates it into the standard input (`stdin`) format that the backend engine understands, runs the engine as a subprocess, and then captures the standard output (`stdout`) to send back as an HTTP response.

This approach allows us to provide a modern API without modifying the core, battle-tested AI backend.

## 2. How to Start the API Server

You can run the API server directly from your terminal.

**Prerequisites:**
- Ensure you have installed all the necessary Python packages. From the `backends/stable_diffusion` directory, run:
  ```bash
  pip install -r requirements.txt
  ```

**Running the Server:**
- Navigate to the `backends/stable_diffusion` directory and run the following command:
  ```bash
  python api_server.py
  ```
- The server will start, and by default, it will be accessible on your local network at `http://<your-local-ip-address>:5001`.

## 3. API Endpoint Specification

### `/api/inpainting`

- **Method:** `POST`
- **Content-Type:** `application/json`
- **Description:** Takes a base image, a mask, and a text prompt, and returns a new image with the masked area filled in according to the prompt.

**JSON Request Body:**

| Key          | Type   | Required | Description                                                                                             |
|--------------|--------|----------|---------------------------------------------------------------------------------------------------------|
| `image_b64`  | String | Yes      | The base image encoded as a Base64 string (with data URI prefix, e.g., `data:image/png;base64,...`).     |
| `mask_b64`   | String | Yes      | The mask image encoded as a Base64 string. White areas indicate where to inpaint, black areas are kept. |
| `prompt`     | String | Yes      | A text description of what to generate in the masked area.                                              |
| `width`      | Int    | No       | The desired width of the output image. Defaults to 512.                                                 |
| `height`     | Int    | No       | The desired height of the output image. Defaults to 512.                                                |
| `steps`      | Int    | No       | The number of diffusion steps. Defaults to 50. More steps can improve quality but take longer.          |
| `seed`       | Int    | No       | A number for controlling generation. Use `-1` or omit for a random seed.                                |

**JSON Success Response (200 OK):**

```json
{
  "generated_img_path": "/path/on/server/to/image.png",
  "generated_img_url": "/images/image.png"
}
```
- `generated_img_path`: The absolute path of the generated image on the server's file system.
- `generated_img_url`: The URL path to retrieve the generated image from the server. The full URL would be `http://<server-ip>:5001/images/image.png`.


## 4. Example Usage in Swift (for Xcode)

Here is a simple example of how you could call this API from a Swift application using `URLSession`.

```swift
import Foundation
import SwiftUI

// Define the structure for our JSON request body
struct InpaintingRequest: Codable {
    let image_b64: String
    let mask_b64: String
    let prompt: String
    let width: Int = 512
    let height: Int = 512
}

// Define the structure for the JSON response
struct InpaintingResponse: Codable {
    let generated_img_url: String
}

// Function to call the API
func performInpainting(baseImage: UIImage, maskImage: UIImage, prompt: String) async throws -> UIImage {
    // 1. Set up the API endpoint
    guard let url = URL(string: "http://127.0.0.1:5001/api/inpainting") else {
        throw URLError(.badURL)
    }

    // 2. Convert UIImages to Base64 strings with data URI prefix
    guard let imageData = baseImage.pngData(), let maskData = maskImage.pngData() else {
        throw URLError(.cannotDecodeContentData)
    }
    let imageBase64 = "data:image/png;base64," + imageData.base64EncodedString()
    let maskBase64 = "data:image/png;base64," + maskData.base64EncodedString()

    // 3. Create the request body
    let requestBody = InpaintingRequest(image_b64: imageBase64, mask_b64: maskBase64, prompt: prompt)
    let jsonData = try JSONEncoder().encode(requestBody)

    // 4. Configure the URLRequest
    var request = URLRequest(url: url)
    request.httpMethod = "POST"
    request.setValue("application/json", forHTTPHeaderField: "Content-Type")
    request.httpBody = jsonData

    // 5. Perform the network request
    let (data, response) = try await URLSession.shared.data(for: request)

    guard let httpResponse = response as? HTTPURLResponse, httpResponse.statusCode == 200 else {
        throw URLError(.badServerResponse)
    }

    // 6. Decode the response to get the image URL
    let result = try JSONDecoder().decode(InpaintingResponse.self, from: data)
    guard let imageUrl = URL(string: "http://127.0.0.1:5001" + result.generated_img_url) else {
        throw URLError(.badURL)
    }

    // 7. Download the resulting image
    let (imageDataResponse, _) = try await URLSession.shared.data(from: imageUrl)

    guard let finalImage = UIImage(data: imageDataResponse) else {
        throw URLError(.cannotDecodeContentData)
    }

    return finalImage
}

// Example usage in a SwiftUI view
struct ContentView: View {
    @State private var resultImage: UIImage?

    var body: some View {
        VStack {
            if let image = resultImage {
                Image(uiImage: image)
                    .resizable()
                    .scaledToFit()
            } else {
                Text("Tap the button to start inpainting...")
            }

            Button("Run Inpainting") {
                Task {
                    do {
                        // Replace with your actual placeholder images
                        let placeholderImage = UIImage(systemName: "photo")!
                        let maskImage = UIImage(systemName: "square.fill")!

                        resultImage = try await performInpainting(
                            baseImage: placeholderImage,
                            maskImage: maskImage,
                            prompt: "a beautiful castle in the sky"
                        )
                    } catch {
                        print("Error: \(error)")
                    }
                }
            }
        }
    }
}
```
