// OpenRemaster WGC HWND-bound single-frame producer, Windows 10 1903+.
// Standalone local native executable. Not an RDC screen capture.
// Exit success only after exact PID+process-creation identity and BMP writing.
// This program does NOT claim fidelity verification.
#define NOMINMAX
#include <windows.h>
#include <d3d11.h>
#include <dxgi.h>
#include <windows.graphics.capture.interop.h>
#include <windows.graphics.directx.direct3d11.interop.h>
#include <winrt/base.h>
#include <winrt/Windows.Foundation.h>
#include <winrt/Windows.Graphics.h>
#include <winrt/Windows.Graphics.Capture.h>
#include <winrt/Windows.Graphics.DirectX.h>
#include <winrt/Windows.Graphics.DirectX.Direct3D11.h>
#include <cstdint>
#include <iostream>
#include <fstream>
#include <filesystem>
#include <chrono>
#include <thread>
#include <vector>
#include <string>
#include <stdexcept>
#include <cstdlib>

#pragma comment(lib, "d3d11.lib")
#pragma comment(lib, "dxgi.lib")
#pragma comment(lib, "windowsapp.lib")
#pragma comment(lib, "user32.lib")

namespace fs = std::filesystem;
using namespace winrt;
namespace WGC = winrt::Windows::Graphics::Capture;
namespace WDX = winrt::Windows::Graphics::DirectX;
namespace WD11 = winrt::Windows::Graphics::DirectX::Direct3D11;

static void must(bool okay, const char* msg) {
    if (!okay) throw std::runtime_error(msg);
}
static unsigned long long ticks(const FILETIME& f) {
    return (static_cast<unsigned long long>(f.dwHighDateTime) << 32) | f.dwLowDateTime;
}
static unsigned long long creation_ticks(DWORD pid) {
    HANDLE p = OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, FALSE, pid);
    must(p != nullptr, "OPEN_PROCESS_FAILED");
    FILETIME created{}, exited{}, kernel{}, user{};
    BOOL ok = GetProcessTimes(p, &created, &exited, &kernel, &user);
    CloseHandle(p);
    must(ok != 0, "GET_PROCESS_TIMES_FAILED");
    return ticks(created);
}
static void assert_identity(HWND hwnd, DWORD pid, unsigned long long expectedTicks) {
    must(IsWindow(hwnd) != 0, "WINDOW_NO_LONGER_EXISTS");
    DWORD owner=0;
    GetWindowThreadProcessId(hwnd, &owner);
    must(owner == pid, "WINDOW_PID_MISMATCH");
    must(creation_ticks(pid) == expectedTicks, "PROCESS_CREATION_TICKS_MISMATCH");
}
#pragma pack(push,1)
struct BmpHeader {
    uint16_t magic = 0x4d42;
    uint32_t total = 0;
    uint16_t reserved1 = 0;
    uint16_t reserved2 = 0;
    uint32_t offset = 54;
    uint32_t dibsize = 40;
    int32_t width = 0;
    int32_t height = 0; // negative => top-down
    uint16_t planes = 1;
    uint16_t bpp = 32;
    uint32_t compression = 0;
    uint32_t imageSize = 0;
    int32_t xppm = 0;
    int32_t yppm = 0;
    uint32_t used = 0;
    uint32_t important = 0;
};
#pragma pack(pop)
static_assert(sizeof(BmpHeader) == 54, "Invalid BMP header size");

static void write_bmp(const fs::path& path, ID3D11Device* device, ID3D11DeviceContext* context, ID3D11Texture2D* source, int width, int height) {
    must(width > 0 && height > 0 && width <= 8192 && height <= 8192, "FRAME_DIMENSIONS_UNSAFE");
    D3D11_TEXTURE2D_DESC desc{};
    source->GetDesc(&desc);
    must(desc.Format == DXGI_FORMAT_B8G8R8A8_UNORM, "UNEXPECTED_PIXEL_FORMAT");
    must(width <= static_cast<int>(desc.Width) && height <= static_cast<int>(desc.Height), "FRAME_LARGER_THAN_TEXTURE");
    desc.Width = width;
    desc.Height = height;
    desc.Usage = D3D11_USAGE_STAGING;
    desc.BindFlags = 0;
    desc.CPUAccessFlags = D3D11_CPU_ACCESS_READ;
    desc.MiscFlags = 0;
    desc.MipLevels = 1;
    desc.ArraySize = 1;
    desc.SampleDesc.Count = 1;
    desc.SampleDesc.Quality = 0;
    com_ptr<ID3D11Texture2D> staging;
    check_hresult(device->CreateTexture2D(&desc, nullptr, staging.put()));
    context->CopySubresourceRegion(staging.get(), 0, 0, 0, 0, source, 0, nullptr);
    D3D11_MAPPED_SUBRESOURCE map{};
    check_hresult(context->Map(staging.get(), 0, D3D11_MAP_READ, 0, &map));
    const size_t stride = static_cast<size_t>(width) * 4;
    const size_t total = stride * static_cast<size_t>(height);
    must(total <= 256 * 1024 * 1024, "FRAME_BYTE_COUNT_UNSAFE");
    std::vector<uint8_t> bytes(total);
    for (int y=0; y<height; ++y) {
        std::memcpy(bytes.data() + static_cast<size_t>(y)*stride,
                    static_cast<const uint8_t*>(map.pData) + static_cast<size_t>(y)*map.RowPitch, stride);
    }
    context->Unmap(staging.get(), 0);
    BmpHeader header;
    header.width = width;
    header.height = -height;
    header.imageSize = static_cast<uint32_t>(total);
    header.total = 54 + header.imageSize;
    std::ofstream out(path, std::ios::binary | std::ios::trunc);
    must(out.good(), "OUTPUT_OPEN_FAILED");
    out.write(reinterpret_cast<const char*>(&header), sizeof(header));
    out.write(reinterpret_cast<const char*>(bytes.data()), static_cast<std::streamsize>(bytes.size()));
    out.flush();
    must(out.good(), "OUTPUT_WRITE_FAILED");
    out.close();
    must(fs::file_size(path) == 54 + total, "OUTPUT_SIZE_MISMATCH");
}
int wmain(int argc, wchar_t** argv) {
    try {
        if (argc != 5) {
            std::cerr << "USAGE capture_window_wgc.exe HWND_DEC PID CREATION_TICKS OUTPUT_BMP\n";
            return 2;
        }
        unsigned long long handleValue = _wcstoui64(argv[1], nullptr, 10);
        unsigned long long ticksValue = _wcstoui64(argv[3], nullptr, 10);
        unsigned long long pid64 = _wcstoui64(argv[2], nullptr, 10);
        must(pid64 > 0 && pid64 <= 0xffffffffULL && handleValue > 0 && ticksValue > 0, "INVALID_IDENTITY_ARGUMENT");
        const DWORD pid = static_cast<DWORD>(pid64);
        auto hwnd = reinterpret_cast<HWND>(static_cast<uintptr_t>(handleValue));
        const fs::path output(argv[4]);
        must(output.is_absolute() && output.extension() == L".bmp", "INVALID_OUTPUT_PATH");
        must(!fs::exists(output), "OUTPUT_ALREADY_EXISTS");
        assert_identity(hwnd, pid, ticksValue);
        init_apartment(apartment_type::multi_threaded);
        com_ptr<ID3D11Device> d3dDevice;
        com_ptr<ID3D11DeviceContext> context;
        UINT flags = D3D11_CREATE_DEVICE_BGRA_SUPPORT;
        HRESULT hr = D3D11CreateDevice(nullptr, D3D_DRIVER_TYPE_HARDWARE, nullptr, flags,
                                       nullptr, 0, D3D11_SDK_VERSION,
                                       d3dDevice.put(), nullptr, context.put());
        if (FAILED(hr)) {
            check_hresult(D3D11CreateDevice(nullptr, D3D_DRIVER_TYPE_WARP, nullptr, flags,
                                            nullptr, 0, D3D11_SDK_VERSION,
                                            d3dDevice.put(), nullptr, context.put()));
        }
        auto dxgi = d3dDevice.as<IDXGIDevice>();
        com_ptr<::IInspectable> inspectable;
        check_hresult(CreateDirect3D11DeviceFromDXGIDevice(dxgi.get(), inspectable.put()));
        auto winrtDevice = inspectable.as<WD11::IDirect3DDevice>();

        auto factory = get_activation_factory<WGC::GraphicsCaptureItem, IGraphicsCaptureItemInterop>();
        WGC::GraphicsCaptureItem item{nullptr};
        check_hresult(factory->CreateForWindow(
            hwnd, guid_of<WGC::GraphicsCaptureItem>(), put_abi(item)));
        const auto size=item.Size();
        must(size.Width > 0 && size.Height > 0, "INVALID_CAPTURE_SIZE");

        auto pool=WGC::Direct3D11CaptureFramePool::CreateFreeThreaded(
            winrtDevice, WDX::DirectXPixelFormat::B8G8R8A8UIntNormalized, 2, size);
        auto session=pool.CreateCaptureSession(item);
        // Omit mouse cursor from deterministic frame comparison.
        session.IsCursorCaptureEnabled(false);
        assert_identity(hwnd,pid,ticksValue);
        session.StartCapture();

        bool success = false;
        int capturedW=0, capturedH=0;
        const auto deadline=std::chrono::steady_clock::now()+std::chrono::seconds(8);
        while(std::chrono::steady_clock::now()<deadline) {
            assert_identity(hwnd,pid,ticksValue);
            auto frame=pool.TryGetNextFrame();
            if(frame) {
                auto contentSize=frame.ContentSize();
                auto surf=frame.Surface();
                auto access=surf.as<::Windows::Graphics::DirectX::Direct3D11::IDirect3DDxgiInterfaceAccess>();
                com_ptr<ID3D11Texture2D> texture;
                check_hresult(access->GetInterface(__uuidof(ID3D11Texture2D), texture.put_void()));
                capturedW=contentSize.Width;
                capturedH=contentSize.Height;
                write_bmp(output,d3dDevice.get(),context.get(),texture.get(),capturedW,capturedH);
                success=true;
                break;
            }
            std::this_thread::sleep_for(std::chrono::milliseconds(30));
        }
        session.Close();
        pool.Close();
        assert_identity(hwnd,pid,ticksValue);
        must(success,"CAPTURE_FRAME_TIMEOUT");
        std::cout<<"{\"schema\":\"OpenRemaster.NativeWGCFrame.v1\",\"backend\":\"windows_graphics_capture\","
                 <<"\"hwnd\":"<<handleValue<<",\"pid\":"<<pid<<",\"creation_ticks_100ns\":"<<ticksValue
                 <<",\"width\":"<<capturedW<<",\"height\":"<<capturedH<<",\"capture_frame_file\":\"frame-0001.bmp\"}\n";
        return 0;
    } catch(const hresult_error& e) {
        std::wcerr << L"WGC_HRESULT_ERROR 0x" << std::hex << static_cast<unsigned int>(e.code().value)
                   << L": " << e.message().c_str() << L"\n";
        return 5;
    } catch (const std::exception& e) {
        std::cerr << "WGC_ERROR: " << e.what() << "\n";
        return 4;
    } catch (...) {
        std::cerr << "WGC_UNKNOWN_ERROR\n";
        return 7;
    }
}
