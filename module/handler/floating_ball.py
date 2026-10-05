from module.base.timer import Timer
from module.device.method.utils import HierarchyButton
from module.handler.assets import (FLOAT_BALL_360, FLOAT_BALL_360_CLOSE,
                                   FLOAT_BALL_360_HIDE)
from module.handler.info_handler import InfoHandler
from module.logger import logger

# The row "隐藏浮球" is a native android view of the 360 assistant panel, finding it by
# text does not depend on the size of the panel.
FLOAT_BALL_360_HIDE_XPATHS = (
    '//*[@text="隐藏浮球"]',
    '//*[contains(@text, "隐藏")]',
)


class FloatingBallHandler(InfoHandler):
    """
    Handle the assistant floating ball of the 360 (qihoo) game client.

    The 360 client draws its own assistant floating ball above the game. The ball is
    docked at the left edge of the screen, only its right half is visible, and it is
    recreated on every game start. Instead of masking it out during recognition, the
    ball is hidden right after login by the ball's own "隐藏浮球" option.
    """

    def _float_ball_appear(self):
        """
        Returns:
            bool: If the floating ball appears on the screen.
        """
        # An integer offset makes Button.match() search vertically only, because the
        # ball is docked at the left edge of the screen but can be dragged up and down.
        # Similarity 0.9 has a large margin: the asset matches 1.000 with the badge
        # digit and 1.000 with the digit gone, 0.980 over a different background.
        return self.appear(FLOAT_BALL_360, offset=60, similarity=0.9)

    def _float_ball_hide_from_hierarchy(self):
        """
        Find the row "隐藏浮球" in the android ui hierarchy.

        Returns:
            HierarchyButton, None:
        """
        try:
            self.device.dump_hierarchy()
        except Exception as e:
            logger.warning(f'Failed to dump ui hierarchy: {e}')
            return None

        for xpath in FLOAT_BALL_360_HIDE_XPATHS:
            row = HierarchyButton(self.device.hierarchy, xpath)
            if row:
                return row
        return None

    def _float_ball_panel_button(self):
        """
        Find the row "隐藏浮球" of the 360 assistant panel.

        The panel is drawn by the 360 SDK and its size follows the screen density, so
        the assets cut from one client are not necessarily at the same place on
        another one. Try the image assets first, then the android view with that text.

        Returns:
            Button, HierarchyButton, None: None if the row is not on the screen.
        """
        # White row with black chinese text. Retry with a lower similarity because the
        # assets were cut from a jpeg screenshot.
        for similarity in (0.85, 0.75):
            if self.appear(FLOAT_BALL_360_HIDE, offset=(30, 30), similarity=similarity):
                return FLOAT_BALL_360_HIDE

        return self._float_ball_hide_from_hierarchy()

    def _float_ball_press_back(self):
        """
        Leave the 360 assistant panel with the android back key.
        """
        self.device.adb_shell(['input', 'keyevent', '4'])

    def _float_ball_leave_panel(self):
        """
        Leave the 360 assistant panel, with its close button, or with the android back
        key if the close button is not where it is expected to be.
        """
        if self.appear_then_click(FLOAT_BALL_360_CLOSE, offset=(30, 30), interval=2):
            return
        self._float_ball_press_back()

    def handle_floating_ball(self):
        """
        Pages:
            in: page_main
            out: page_main

        Returns:
            bool: If handled.
        """
        # The ball is created by the 360 SDK when the game starts, it may be a bit later
        # than the moment we reached page_main.
        appear_timer = Timer(3).start()
        while 1:
            self.device.screenshot()
            if self._float_ball_appear():
                break
            if appear_timer.reached():
                logger.info('360 floating ball not found')
                return False

        # Click the ball to open the 360 assistant panel, click "隐藏浮球", then leave
        # the panel. The panel would break every recognition if it was left open.
        # The panel is a drawer on the left half of the screen, the game behind it is
        # still visible, so it must not be confused with the game page.
        logger.hr('360 floating ball', level=2)
        ball_clicks = 0
        hide_clicks = 0
        hide_clicked = False
        back_count = 0
        back_timer = Timer(1.5).start()
        timeout = Timer(15).start()
        while 1:
            self.device.screenshot()

            if self._float_ball_appear():
                # The ball is on the screen, the panel is not covering it
                if ball_clicks < 2 \
                        and self.appear_then_click(FLOAT_BALL_360, offset=60, similarity=0.9, interval=3):
                    ball_clicks += 1
                    continue
            else:
                # The ball is covered by the 360 assistant panel, or it is gone
                row = self._float_ball_panel_button()
                if row is not None:
                    # The panel is open, click the row "隐藏浮球"
                    if hide_clicks < 2:
                        hide_clicks += 1
                        hide_clicked = True
                        logger.info(f'UI additional: {row} -> click')
                        self.device.click(row)
                        continue
                elif hide_clicked:
                    # "隐藏浮球" was clicked and its row is gone, the panel is closed
                    logger.info('360 floating ball hidden')
                    return True

                # Cannot hide it, leave the panel
                if back_count < 3 and back_timer.reached():
                    self._float_ball_leave_panel()
                    back_count += 1
                    back_timer.reset()
                    continue

            if timeout.reached():
                logger.warning('Failed to hide the 360 floating ball')
                break

        # Failed, keep a screenshot and the ui hierarchy for debugging, and never leave
        # the panel open
        self.device.save_screenshot(genre='360_float_ball')
        self._float_ball_hide_from_hierarchy()
        if hasattr(self.device, 'hierarchy'):
            texts = [node.get('text') for node in self.device.hierarchy.xpath('//*[@text]') if node.get('text')]
            logger.warning(f'360 floating ball: ui hierarchy texts: {texts[:20]}')
        for _ in range(3):
            self.device.screenshot()
            if self._float_ball_appear():
                break
            self._float_ball_press_back()
        return False
