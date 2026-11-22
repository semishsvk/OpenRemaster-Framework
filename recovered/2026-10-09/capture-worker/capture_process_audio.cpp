// OpenRemaster local Windows 11 WASAPI process-loopback capture.
// Target process tree only (never desktop-mix recording).
// This captures audio evidence; it does not attest whether playback is faithful.
#define NOMINMAX
#include <Windows.h>
#include <audioclient.h>
#include <audioclientactivationparams.h>
#include <mmdeviceapi.h>
#include <propidl.h>
#include <wrl/client.h>
#include <wrl/implements.h>
#include <cstdint>
#include <atomic>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <vector>
#include <thread>
#include <chrono>
#include <cstring>

#pragma comment(lib, "mmdevapi.lib")
#pragma comment(lib, "ole32.lib")
#pragma comment(lib, "user32.lib")

using Microsoft::WRL::ComPtr;
namespace fs=std::filesystem;

static void ensure(bool b,const char* message) {
    if(!b)throw std::runtime_error(message);
}
static void checked(HRESULT hr,const char* message) {
    if(FAILED(hr)) {
        char s[128];
        sprintf_s(s,"%s: 0x%08X",message,static_cast<unsigned int>(hr));
        throw std::runtime_error(s);
    }
}
static unsigned long long fromFILETIME(const FILETIME& t) {
    return (static_cast<unsigned long long>(t.dwHighDateTime)<<32) | t.dwLowDateTime;
}
static unsigned long long ownerCreation(DWORD pid) {
    HANDLE p=OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION,FALSE,pid);
    ensure(p!=nullptr,"TARGET_PROCESS_UNAVAILABLE");
    FILETIME a{},b{},c{},d{};
    BOOL okay=GetProcessTimes(p,&a,&b,&c,&d);
    CloseHandle(p);
    ensure(okay!=0,"TARGET_CREATION_QUERY_FAILED");
    return fromFILETIME(a);
}
class ActivationHandler final :
    public Microsoft::WRL::RuntimeClass<
      Microsoft::WRL::RuntimeClassFlags<Microsoft::WRL::ClassicCom>,
      Microsoft::WRL::FtmBase,
      IActivateAudioInterfaceCompletionHandler> {
public:
    HANDLE eventHandle=nullptr;
    HRESULT result=E_PENDING;
    ComPtr<IAudioClient> client;

    ActivationHandler() {
        eventHandle=CreateEventW(nullptr,FALSE,FALSE,nullptr);
    }
    ~ActivationHandler() {
        if(eventHandle)CloseHandle(eventHandle);
    }
    STDMETHOD(ActivateCompleted)(IActivateAudioInterfaceAsyncOperation* operation) override {
        HRESULT activationHr=E_FAIL;
        ComPtr<IUnknown> audioUnknown;
        HRESULT hr=operation->GetActivateResult(&activationHr,audioUnknown.GetAddressOf());
        if(SUCCEEDED(hr))hr=activationHr;
        if(SUCCEEDED(hr))hr=audioUnknown.As(&client);
        result=hr;
        SetEvent(eventHandle);
        return S_OK;
    }
};
#pragma pack(push,1)
struct WavHeader {
    char riff[4]={'R','I','F','F'};
    uint32_t riffSize=0;
    char wave[4]={'W','A','V','E'};
    char fmt[4]={'f','m','t',' '};
    uint32_t fmtSize=16;
    uint16_t format=1;
    uint16_t channels=2;
    uint32_t sampleRate=44100;
    uint32_t byteRate=44100*4;
    uint16_t blockAlign=4;
    uint16_t bitsPerSample=16;
    char data[4]={'d','a','t','a'};
    uint32_t dataSize=0;
};
#pragma pack(pop)
static_assert(sizeof(WavHeader)==44,"Unexpected WAV header size");

static size_t countNonzero(const std::vector<BYTE>& bytes) {
    size_t nonzero=0;
    for(size_t i=0;i<bytes.size();i+=2) {
        int16_t sample=0;
        std::memcpy(&sample,bytes.data()+i,2);
        if(sample!=0)nonzero++;
    }
    return nonzero;
}
int wmain(int argc,wchar_t** argv) {
    try {
        if(argc!=5) {
            std::cerr<<"USAGE capture_process_audio.exe PID CREATION_TICKS DURATION_MS OUT_WAV\n";
            return 2;
        }
        auto rawpid=_wcstoui64(argv[1],nullptr,10);
        auto expectedTicks=_wcstoui64(argv[2],nullptr,10);
        auto durationms=_wcstoui64(argv[3],nullptr,10);
        ensure(rawpid>0 && rawpid<=0xffffffffull && expectedTicks>0 && durationms>=250 && durationms<=30000,"INVALID_ARGUMENT");
        DWORD pid=static_cast<DWORD>(rawpid);
        fs::path path(argv[4]);
        ensure(path.is_absolute() && path.extension()==L".wav" && !fs::exists(path),"INVALID_OUTPUT_PATH");
        ensure(ownerCreation(pid)==expectedTicks,"TARGET_IDENTITY_CHANGED");

        HRESULT cohr=CoInitializeEx(nullptr,COINIT_MULTITHREADED);
        checked(cohr,"COM_INITIALIZE_FAILED");
        auto endcom=[](){CoUninitialize();};
        auto handler=Microsoft::WRL::Make<ActivationHandler>();
        ensure(handler && handler->eventHandle,"AUDIO_COMPLETION_HANDLER_FAILED");

        AUDIOCLIENT_ACTIVATION_PARAMS ap{};
        ap.ActivationType=AUDIOCLIENT_ACTIVATION_TYPE_PROCESS_LOOPBACK;
        ap.ProcessLoopbackParams.TargetProcessId=pid;
        ap.ProcessLoopbackParams.ProcessLoopbackMode=PROCESS_LOOPBACK_MODE_INCLUDE_TARGET_PROCESS_TREE;
        PROPVARIANT prop{};
        prop.vt=VT_BLOB;
        prop.blob.cbSize=sizeof(ap);
        prop.blob.pBlobData=reinterpret_cast<BYTE*>(&ap);
        ComPtr<IActivateAudioInterfaceAsyncOperation> async;
        checked(ActivateAudioInterfaceAsync(VIRTUAL_AUDIO_DEVICE_PROCESS_LOOPBACK, __uuidof(IAudioClient),
                                             &prop,handler.Get(),async.GetAddressOf()),
                "AUDIO_PROCESS_ACTIVATION_FAILED");
        ensure(WaitForSingleObject(handler->eventHandle,10000)==WAIT_OBJECT_0,"AUDIO_ACTIVATION_TIMEOUT");
        checked(handler->result,"AUDIO_ACTIVATION_RESULT_FAILED");
        auto audio=handler->client;
        ensure(audio!=nullptr,"AUDIO_CLIENT_UNAVAILABLE");

        WAVEFORMATEX fmt{};
        fmt.wFormatTag=WAVE_FORMAT_PCM;
        fmt.nChannels=2;
        fmt.nSamplesPerSec=44100;
        fmt.wBitsPerSample=16;
        fmt.nBlockAlign=fmt.nChannels*fmt.wBitsPerSample/8;
        fmt.nAvgBytesPerSec=fmt.nSamplesPerSec*fmt.nBlockAlign;
        fmt.cbSize=0;
        checked(audio->Initialize(AUDCLNT_SHAREMODE_SHARED,
                 AUDCLNT_STREAMFLAGS_LOOPBACK | AUDCLNT_STREAMFLAGS_EVENTCALLBACK |
                 AUDCLNT_STREAMFLAGS_AUTOCONVERTPCM,
                 0,0,&fmt,nullptr),"AUDIO_CLIENT_INITIALIZE_FAILED");
        ComPtr<IAudioCaptureClient> capture;
        checked(audio->GetService(IID_PPV_ARGS(&capture)),"AUDIO_CAPTURE_SERVICE_FAILED");
        HANDLE ready=CreateEventW(nullptr,FALSE,FALSE,nullptr);
        ensure(ready!=nullptr,"AUDIO_READY_EVENT_FAILED");
        checked(audio->SetEventHandle(ready),"AUDIO_SET_EVENT_FAILED");
        ensure(ownerCreation(pid)==expectedTicks,"TARGET_IDENTITY_CHANGED_PRESTART");
        checked(audio->Start(),"AUDIO_START_FAILED");
        std::vector<BYTE> bytes;
        bytes.reserve(static_cast<size_t>(durationms)*44100*4/1000+16384);
        size_t frames=0;
        size_t samplePackets=0;
        const auto until=std::chrono::steady_clock::now()+std::chrono::milliseconds(durationms);
        while(std::chrono::steady_clock::now()<until) {
            ensure(ownerCreation(pid)==expectedTicks,"TARGET_IDENTITY_CHANGED_DURING_AUDIO");
            WaitForSingleObject(ready,80);
            UINT32 packets=0;
            checked(capture->GetNextPacketSize(&packets),"AUDIO_PACKET_SIZE_FAILED");
            while(packets>0) {
                BYTE* raw=nullptr;
                UINT32 n=0;
                DWORD flags=0;
                checked(capture->GetBuffer(&raw,&n,&flags,nullptr,nullptr),"AUDIO_GET_BUFFER_FAILED");
                size_t size=static_cast<size_t>(n)*fmt.nBlockAlign;
                ensure(bytes.size()+size < 64*1024*1024,"AUDIO_CAPTURE_TOO_LARGE");
                if(flags & AUDCLNT_BUFFERFLAGS_SILENT) {
                    bytes.insert(bytes.end(),size,0);
                } else {
                    ensure(raw!=nullptr,"AUDIO_PACKET_NULL_POINTER");
                    bytes.insert(bytes.end(),raw,raw+size);
                }
                frames+=n;
                samplePackets++;
                checked(capture->ReleaseBuffer(n),"AUDIO_RELEASE_BUFFER_FAILED");
                checked(capture->GetNextPacketSize(&packets),"AUDIO_PACKET_SIZE_FAILED");
            }
        }
        checked(audio->Stop(),"AUDIO_STOP_FAILED");
        CloseHandle(ready);
        ensure(ownerCreation(pid)==expectedTicks,"TARGET_IDENTITY_CHANGED_POST_CAPTURE");
        ensure(bytes.size()<=0xffffffffu-44u,"AUDIO_RIFF_SIZE_LIMIT");
        WavHeader header{};
        header.dataSize=static_cast<uint32_t>(bytes.size());
        header.riffSize=header.dataSize+36;
        std::ofstream out(path,std::ios::binary|std::ios::trunc);
        ensure(out.good(),"WAV_OUTPUT_OPEN_FAILED");
        out.write(reinterpret_cast<const char*>(&header),sizeof(header));
        if(!bytes.empty())out.write(reinterpret_cast<const char*>(bytes.data()),static_cast<std::streamsize>(bytes.size()));
        out.flush();
        ensure(out.good(),"WAV_OUTPUT_WRITE_FAILED");
        out.close();
        ensure(fs::file_size(path)==bytes.size()+44,"WAV_OUTPUT_LENGTH_MISMATCH");
        size_t nonzero=countNonzero(bytes);
        endcom();
        std::cout<<"{\"schema\":\"OpenRemaster.ProcessLoopbackAudio.v1\",\"backend\":\"process_loopback\","
                 <<"\"pid\":"<<pid<<",\"creation_ticks_100ns\":"<<expectedTicks
                 <<",\"duration_ms\":"<<durationms<<",\"sample_rate\":44100,\"channels\":2,"
                 <<"\"bits_per_sample\":16,\"frames\":"<<frames<<",\"packets\":"<<samplePackets
                 <<",\"nonzero_samples\":"<<nonzero<<",\"audio_file\":\"process-0001.wav\"}\n";
        return 0;
    } catch(const std::exception& e) {
        std::cerr<<"PROCESS_LOOPBACK_ERROR: "<<e.what()<<"\n";
        return 4;
    } catch(...) {
        std::cerr<<"PROCESS_LOOPBACK_UNKNOWN_ERROR\n";
        return 5;
    }
}
