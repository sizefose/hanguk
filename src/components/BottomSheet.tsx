"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

type BottomSheetRenderArgs = {
  requestClose: () => void;
};

type BottomSheetProps = {
  overlayClassName: string;
  sheetClassName: string;
  dragZoneClassName: string;
  grabberClassName: string;
  overlayAlphaVar: string;
  overlayBaseAlpha?: number;
  closeThreshold?: number;
  maxDragDistance?: number;
  openDurationMs?: number;
  closeDurationMs?: number;
  onRequestClose: () => void;
  children: React.ReactNode | ((args: BottomSheetRenderArgs) => React.ReactNode);
};

type BodyLockSnapshot = {
  overflow: string;
  touchAction: string;
  position: string;
  top: string;
  left: string;
  right: string;
  width: string;
};

let bodyLockDepth = 0;
let bodyLockScrollY = 0;
let bodyLockSnapshot: BodyLockSnapshot | null = null;

const lockBodyScroll = () => {
  if (bodyLockDepth === 0) {
    bodyLockScrollY = window.scrollY;
    bodyLockSnapshot = {
      overflow: document.body.style.overflow,
      touchAction: document.body.style.touchAction,
      position: document.body.style.position,
      top: document.body.style.top,
      left: document.body.style.left,
      right: document.body.style.right,
      width: document.body.style.width,
    };

    document.body.style.overflow = "hidden";
    document.body.style.touchAction = "none";
    document.body.style.position = "fixed";
    document.body.style.top = `-${bodyLockScrollY}px`;
    document.body.style.left = "0";
    document.body.style.right = "0";
    document.body.style.width = "100%";
  }
  bodyLockDepth += 1;
};

const unlockBodyScroll = () => {
  if (bodyLockDepth <= 0) {
    return;
  }
  bodyLockDepth -= 1;
  if (bodyLockDepth !== 0) {
    return;
  }
  if (!bodyLockSnapshot) {
    return;
  }

  document.body.style.overflow = bodyLockSnapshot.overflow;
  document.body.style.touchAction = bodyLockSnapshot.touchAction;
  document.body.style.position = bodyLockSnapshot.position;
  document.body.style.top = bodyLockSnapshot.top;
  document.body.style.left = bodyLockSnapshot.left;
  document.body.style.right = bodyLockSnapshot.right;
  document.body.style.width = bodyLockSnapshot.width;
  window.scrollTo(0, bodyLockScrollY);
  bodyLockSnapshot = null;
};

export default function BottomSheet({
  overlayClassName,
  sheetClassName,
  dragZoneClassName,
  grabberClassName,
  overlayAlphaVar,
  overlayBaseAlpha = 0.5,
  closeThreshold = 120,
  maxDragDistance = 320,
  openDurationMs = 320,
  closeDurationMs = 460,
  onRequestClose,
  children,
}: BottomSheetProps) {
  const [dragY, setDragY] = useState(0);
  const [isDragging, setIsDragging] = useState(false);
  const [isClosing, setIsClosing] = useState(false);
  const startY = useRef<number | null>(null);
  const onRequestCloseRef = useRef(onRequestClose);
  const isMountedRef = useRef(true);
  const [isDesktopModal, setIsDesktopModal] = useState(false);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const mq = window.matchMedia("(min-width: 768px) and (orientation: landscape)");
    const apply = () => setIsDesktopModal(mq.matches);
    apply();
    mq.addEventListener("change", apply);
    return () => mq.removeEventListener("change", apply);
  }, []);

  const effectiveOpenDurationMs = isDesktopModal ? 0 : openDurationMs;
  const effectiveCloseDurationMs = isDesktopModal ? 0 : closeDurationMs;

  useEffect(() => {
    onRequestCloseRef.current = onRequestClose;
  }, [onRequestClose]);

  useEffect(() => {
    return () => {
      isMountedRef.current = false;
    };
  }, []);

  const resetSheetState = useCallback(() => {
    if (!isMountedRef.current) return;
    startY.current = null;
    setIsClosing(false);
    setIsDragging(false);
    setDragY(0);
  }, []);

  const requestClose = useCallback(() => {
    if (isClosing) {
      return;
    }

    setIsClosing(true);
    setIsDragging(false);
    setDragY(isDesktopModal ? 0 : maxDragDistance);
  }, [isClosing, isDesktopModal, maxDragDistance]);

  useEffect(() => {
    if (!isClosing) {
      return;
    }

    const timerId = window.setTimeout(() => {
      onRequestCloseRef.current();
      // Important for intercepted/parallel routes: component can stay mounted.
      // Without reset, `isClosing` may remain true and prevent reopening.
      window.setTimeout(() => {
        resetSheetState();
      }, 0);
    }, effectiveCloseDurationMs);

    return () => {
      window.clearTimeout(timerId);
    };
  }, [effectiveCloseDurationMs, isClosing, resetSheetState]);

  useEffect(() => {
    if (isDesktopModal) {
      return;
    }
    lockBodyScroll();

    return () => {
      unlockBodyScroll();
    };
  }, [isDesktopModal]);

  const handlePointerDown = (event: React.PointerEvent<HTMLDivElement>) => {
    if (isClosing || isDesktopModal) return;
    startY.current = event.clientY;
    setIsDragging(true);
    event.currentTarget.setPointerCapture(event.pointerId);
  };

  const handlePointerMove = (event: React.PointerEvent<HTMLDivElement>) => {
    if (isClosing || isDesktopModal || startY.current === null) return;
    const delta = event.clientY - startY.current;
    if (delta > 0) {
      setDragY(delta);
    }
  };

  const handlePointerUp = () => {
    if (isClosing || isDesktopModal || startY.current === null) return;
    if (dragY > closeThreshold) {
      requestClose();
    } else {
      setDragY(0);
    }
    startY.current = null;
    setIsDragging(false);
  };

  const overlayAlpha = useMemo(() => {
    const offset = isClosing ? (isDesktopModal ? 0 : maxDragDistance) : dragY;
    const progress = maxDragDistance > 0 ? Math.min(offset / maxDragDistance, 1) : 0;
    return Math.max(0, overlayBaseAlpha * (1 - progress));
  }, [dragY, isClosing, isDesktopModal, maxDragDistance, overlayBaseAlpha]);

  const overlayStyle = {
    [overlayAlphaVar as never]: overlayAlpha,
  } as React.CSSProperties;

  const sheetStyle: React.CSSProperties = {
    transform:
      isClosing && !isDesktopModal ? "translateY(100%)" : `translateY(${dragY}px)`,
    transition: isDragging
      ? "none"
      : isClosing
        ? `transform ${effectiveCloseDurationMs}ms ease`
        : `transform ${effectiveOpenDurationMs}ms ease`,
    willChange: "transform",
    pointerEvents: isClosing ? "none" : "auto",
  };

  const content =
    typeof children === "function"
      ? children({ requestClose })
      : children;

  return (
    <div className={overlayClassName} style={overlayStyle} onClick={requestClose}>
      <div
        className={`${sheetClassName} is-open ${isDragging ? "is-dragging" : ""} ${
          isClosing ? "is-closing" : ""
        }`}
        style={sheetStyle}
        onClick={(event) => event.stopPropagation()}
      >
        <div
          className={dragZoneClassName}
          onPointerDown={handlePointerDown}
          onPointerMove={handlePointerMove}
          onPointerUp={handlePointerUp}
          onPointerCancel={handlePointerUp}
        >
          <div className={grabberClassName} />
        </div>
        {content}
      </div>
    </div>
  );
}
