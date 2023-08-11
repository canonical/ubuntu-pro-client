from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from ubuntupro.messages import NamedMessage

StaticAffordance = Tuple[NamedMessage, Callable[[], Any], bool]

MessagingOperations = List[Union[str, Tuple[Callable, Dict]]]
MessagingOperationsDict = Dict[str, Optional[MessagingOperations]]
