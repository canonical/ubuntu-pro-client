from typing import Any, Callable, Dict, List, Optional, Tuple, Union

StaticAffordance = Tuple[str, Callable[[], Any], bool]

MessagingOperations = List[Union[str, Tuple[Callable, Dict]]]
MessagingOperationsDict = Dict[str, Optional[MessagingOperations]]
