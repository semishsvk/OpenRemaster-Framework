#define WIN32_LEAN_AND_MEAN
#include <Windows.h>
#pragma comment(lib,"user32.lib")
#pragma comment(lib,"gdi32.lib")
static bool g_owned_key_seen=false;
static LRESULT CALLBACK FrameProc(HWND hwnd,UINT msg,WPARAM wp,LPARAM lp) {
    switch(msg) {
      case WM_PAINT: {
        PAINTSTRUCT p{};
        HDC dc=BeginPaint(hwnd,&p);
        RECT r{};
        GetClientRect(hwnd,&r);
        RECT left{0,0,(r.right-r.left)/2,r.bottom};
        RECT right{left.right,0,r.right,r.bottom};
        HBRUSH red=CreateSolidBrush(g_owned_key_seen?RGB(0,250,0):RGB(250,0,0));
        HBRUSH blue=CreateSolidBrush(g_owned_key_seen?RGB(252,252,0):RGB(0,0,252));
        FillRect(dc,&left,red);
        FillRect(dc,&right,blue);
        DeleteObject(red);
        DeleteObject(blue);
        EndPaint(hwnd,&p);
        return 0;
      }
      case WM_KEYDOWN:
        if(wp==VK_SPACE) { g_owned_key_seen=true;InvalidateRect(hwnd,nullptr,FALSE);return 0; }
        return DefWindowProcW(hwnd,msg,wp,lp);
      case WM_LBUTTONDOWN:
        g_owned_key_seen=true;
        InvalidateRect(hwnd,nullptr,FALSE);
        return 0;
      case WM_TIMER: DestroyWindow(hwnd);return 0;
      case WM_CLOSE: DestroyWindow(hwnd);return 0;
      case WM_DESTROY: PostQuitMessage(0);return 0;
      default: return DefWindowProcW(hwnd,msg,wp,lp);
    }
}
int WINAPI wWinMain(HINSTANCE h,HINSTANCE,PWSTR,int) {
    WNDCLASSEXW wc{};
    wc.cbSize=sizeof(wc);
    wc.hInstance=h;
    wc.lpfnWndProc=FrameProc;
    wc.lpszClassName=L"OpenRemasterFidelityFixture.v1";
    wc.hCursor=LoadCursorW(nullptr,MAKEINTRESOURCEW(32512));
    if (!RegisterClassExW(&wc)) return 5;
    HWND hwnd=CreateWindowExW(WS_EX_NOACTIVATE,wc.lpszClassName,
       L"OpenRemaster Fixture (Bound HWND)",WS_OVERLAPPEDWINDOW,
       280,180,620,440,nullptr,nullptr,h,nullptr);
    if (!hwnd) return 6;
    ShowWindow(hwnd,SW_SHOWNOACTIVATE);
    UpdateWindow(hwnd);
    SetTimer(hwnd,1,20000,nullptr);
    MSG m{};
    while(GetMessageW(&m,nullptr,0,0)>0) {
      TranslateMessage(&m);
      DispatchMessageW(&m);
    }
    return 0;
}
