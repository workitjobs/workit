# Workers out of the student's view

**Status (2026-11-15):** Research only, nothing built. F10 of `../../../docs/desktop_application_auto_apply.md` holds the options that can still be built; this note holds the tests behind it and the helper to repeat them.

Tested on a Mac with macOS 26.0.1, Chrome for Testing from Playwright 1.64, on branch KAN-850.

**The problem.** Each Worker is its own Chrome process, with its own profile. On the Mac, five Workers are five Chrome icons in the Dock, five apps in Cmd-Tab and five windows in Mission Control (a three-finger swipe up). The student finds this cluttered. W5's window shows every Worker as a tile, so the student needs none of these windows.

## 1. Each Worker is its own Dock app

Two plain Workers (`PlainWorkers(kind="testing")`, `launch(0)`, `launch(1)`), read with `lsappinfo list`:

| | Chrome for Testing apps of type Foreground (Dock apps) |
|---|---|
| Before | 1 (another session's) |
| With two Workers | 3: the one before, and one for each Worker |

macOS gives each running copy of an app its own Dock icon and Cmd-Tab entry. It cannot group separate processes.

## 2. A hidden Worker draws nothing

A plain Worker on a page that counts animation frames (`requestAnimationFrame`) and timer ticks (`setInterval`, every 0.1 s). The app was hidden as Cmd-H hides it (`System Events`, `set visible ... to false`), which takes its windows out of Mission Control. Each row is 3 s:

| | Frames | Ticks | `document.visibilityState` | `tabs.screenshot` |
|---|---|---|---|---|
| Shown | 180 | 30 | visible | works |
| Hidden | 0 | 3 | hidden | fails (no answer in 5 s) |
| Hidden, with `--disable-renderer-backgrounding` and `--disable-background-timer-throttling` | 0 | 30 | hidden | fails |

The flags keep the page's scripts running, but nothing is drawn: the tiles would freeze, and job sites would see a hidden page. A minimized window is the same (`docs/plain-workers/PROTOCOL.md`: Workers are never minimized).

## 3. A Worker on a virtual screen draws normally

macOS's private `CGVirtualDisplay` classes (in CoreGraphics; found at run time with `NSClassFromString` on macOS 26.0.1) make a screen that no one sees. The helper below made a 1920 × 1080 screen. macOS put it to the right of the main screen (bounds 1512, 0, 1920, 1080 beside a 1512 × 982 main screen). Chrome for Testing started there with `--window-position` and measured over CDP, 3 s:

| | Result |
|---|---|
| Window | at (1832, 106), on a 1920 × 1080 screen: the virtual one |
| Frames | 181 (60 a second) |
| Ticks | 30 |
| `document.visibilityState` | visible |
| `page.screenshot()` | works (the page was fully drawn) |
| `Page.startScreencast` | works: it sends a frame each time the page changes |

Also seen:

- `system_profiler SPDisplaysDataType` lists it ("WorkIt Workers (test)", 1920 × 1080, Mirror Off), so System Settings, Displays, shows it too.
- It sits beside the main screen, so the pointer can move onto it and seem to vanish.
- It lives only while the process that made it runs (section 4).

**Mission Control: the Worker does not show** (checked by hand, 2026-11-15). With the helper and a Chrome window on the virtual screen running for 60 s, a three-finger swipe up on the main screen did not show that window: macOS shows each screen's own windows on that screen. The session itself could not check it (macOS refused `screencapture` without Screen Recording permission, and `osascript` may not send keys), so a person looked. To check again: run the helper and the Chrome start below, then swipe up with three fingers.

## 4. When the screen's holder dies, its windows move to the student's screen

The helper was killed with SIGKILL, as a crash ends a process, while a Chrome for Testing window was on its screen. Read over CDP:

| | Window x | Screen the page sees | Chrome |
|---|---|---|---|
| Before | 2022 | 1920 × 1080 (virtual) | running, drawing |
| 3 s after the helper died | 306 | 1512 × 982 (the main screen) | still running, drawing |

macOS removes the screen as it removes an unplugged monitor, and moves its windows onto a screen that stays. Workers outlive Apply on purpose (restart recovery), so whatever holds the screen must outlive Apply too.

## The helper

`vd.m`, built with `clang -fobjc-arc -framework Foundation -framework CoreGraphics -framework AppKit vd.m -o vd`. It prints the screen's ID and bounds, and keeps the screen until it gets SIGTERM.

```objc
#import <Foundation/Foundation.h>
#import <CoreGraphics/CoreGraphics.h>

@interface NSObject (VirtualDisplay)
- (instancetype)initWithDescriptor:(id)descriptor;
- (instancetype)initWithWidth:(NSUInteger)width height:(NSUInteger)height refreshRate:(double)refreshRate;
- (BOOL)applySettings:(id)settings;
- (unsigned int)displayID;
@end

int main(void) {
  @autoreleasepool {
    id descriptor = [[NSClassFromString(@"CGVirtualDisplayDescriptor") alloc] init];
    [descriptor setValue:dispatch_get_main_queue() forKey:@"queue"];
    [descriptor setValue:@"WorkIt Workers (test)" forKey:@"name"];
    [descriptor setValue:@1920 forKey:@"maxPixelsWide"];
    [descriptor setValue:@1080 forKey:@"maxPixelsHigh"];
    [descriptor setValue:[NSValue valueWithSize:NSMakeSize(600, 340)] forKey:@"sizeInMillimeters"];
    [descriptor setValue:@0x5754 forKey:@"vendorID"];
    [descriptor setValue:@0x0001 forKey:@"productID"];
    [descriptor setValue:@0x0001 forKey:@"serialNum"];
    id display = [[NSClassFromString(@"CGVirtualDisplay") alloc] initWithDescriptor:descriptor];
    if (!display) { printf("error: no virtual display\n"); return 1; }
    id mode = [[NSClassFromString(@"CGVirtualDisplayMode") alloc] initWithWidth:1920 height:1080 refreshRate:60];
    id settings = [[NSClassFromString(@"CGVirtualDisplaySettings") alloc] init];
    [settings setValue:@[mode] forKey:@"modes"];
    [settings setValue:@0 forKey:@"hiDPI"];
    if (![display applySettings:settings]) { printf("error: settings refused\n"); return 1; }
    unsigned int id_ = [display displayID];
    [NSThread sleepForTimeInterval:1.0];
    CGRect bounds = CGDisplayBounds(id_);
    printf("display %u bounds %.0f %.0f %.0f %.0f\n", id_, bounds.origin.x, bounds.origin.y,
           bounds.size.width, bounds.size.height);
    fflush(stdout);
    CFRunLoopRun();  // keeps the display; SIGTERM ends it
  }
  return 0;
}
```

Then start a Chrome inside its bounds, with a scratch profile: `"<Chrome for Testing>" --user-data-dir=<scratch folder> --no-first-run --remote-debugging-port=0 --window-position=<x + 100>,<y + 100> --window-size=1280,900 <a page>`. Read the page over CDP (`connect_over_cdp`), as the table above did. Stop Chrome first, then the helper.
