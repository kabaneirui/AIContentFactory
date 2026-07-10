from app.models.content_memory import LifecycleStatus

VALID_TRANSITIONS: dict[LifecycleStatus, set[LifecycleStatus]] = {
    LifecycleStatus.CREATED: {
        LifecycleStatus.PUBLISHED,
        LifecycleStatus.TAGGED,
        LifecycleStatus.ARCHIVED,
    },
    LifecycleStatus.PUBLISHED: {
        LifecycleStatus.SYNCING,
        LifecycleStatus.TAGGED,
        LifecycleStatus.ARCHIVED,
    },
    LifecycleStatus.SYNCING: {
        LifecycleStatus.TAGGED,
        LifecycleStatus.PUBLISHED,
        LifecycleStatus.ARCHIVED,
    },
    LifecycleStatus.TAGGED: {
        LifecycleStatus.LEARNED,
        LifecycleStatus.SYNCING,
        LifecycleStatus.ARCHIVED,
    },
    LifecycleStatus.LEARNED: {LifecycleStatus.ARCHIVED},
    LifecycleStatus.ARCHIVED: set(),
}


class InvalidLifecycleTransition(Exception):
    def __init__(self, current: LifecycleStatus, target: LifecycleStatus) -> None:
        super().__init__(
            f"Cannot transition lifecycle from '{current.value}' to '{target.value}'"
        )
        self.current = current
        self.target = target


def can_transition(current: LifecycleStatus, target: LifecycleStatus) -> bool:
    if current == target:
        return True
    return target in VALID_TRANSITIONS.get(current, set())


def transition(current: LifecycleStatus, target: LifecycleStatus) -> LifecycleStatus:
    if current == target:
        return current
    if not can_transition(current, target):
        raise InvalidLifecycleTransition(current, target)
    return target


def initial_status_for_video(*, has_publish_time: bool) -> LifecycleStatus:
    return LifecycleStatus.PUBLISHED if has_publish_time else LifecycleStatus.CREATED
